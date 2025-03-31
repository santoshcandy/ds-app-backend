from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, EmployeeClientDetails,Attendance,MonthlyTarget
from django.conf import settings
from datetime import date
User = get_user_model()

# ✅ Serializer for User Registration
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number", "dob", "role", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            phone_number=validated_data["phone_number"],
            dob=validated_data["dob"],
            role=validated_data["role"],
            password=validated_data["password"]
        )
        return user


# ✅ Serializer for User Login
class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    dob = serializers.DateField()
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    password = serializers.CharField(write_only=True)


# ✅ Serializer for Viewing User Data
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "phone_number", "dob"]


# ✅ Serializer for Clients (Direct & Employee-Registered)
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


# # ✅ Serializer for Employee-Registered Clients (Sensitive Data)
# class EmployeeClientDetailsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EmployeeClientDetails
#         fields = "__all__"

class EmployeeClientDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeClientDetails
        fields = "__all__"

# class EmployeeClientDetailsSerializer(serializers.ModelSerializer):
#     aadhaar_front = serializers.SerializerMethodField()
#     aadhaar_back = serializers.SerializerMethodField()
#     cibil_report = serializers.SerializerMethodField()
#     pan_card = serializers.SerializerMethodField()
#     gas_bill = serializers.SerializerMethodField()

#     def get_full_url(self, file_field):
#         """Convert relative file path to full URL."""
#         if file_field:
#             request = self.context.get("request")
#             return request.build_absolute_uri(settings.MEDIA_URL + str(file_field)) if request else f"{settings.MEDIA_URL}{file_field}"
#         return None

#     def get_aadhaar_front(self, obj):
#         return self.get_full_url(obj.aadhaar_front)

#     def get_aadhaar_back(self, obj):
#         return self.get_full_url(obj.aadhaar_back)

#     def get_cibil_report(self, obj):
#         return self.get_full_url(obj.cibil_report)

#     def get_pan_card(self, obj):
#         return self.get_full_url(obj.pan_card)

#     def get_gas_bill(self, obj):
#         return self.get_full_url(obj.gas_bill)

#     class Meta:
#         model = EmployeeClientDetails
#         fields = "__all__"



class AttendanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'user', 'date', 'status']


class MonthlyTargetSerializer(serializers.ModelSerializer):
    month = serializers.IntegerField(default=date.today().month)
    year = serializers.IntegerField(default=date.today().year)
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="employee"), required=False, allow_null=True
    )

    class Meta:
        model = MonthlyTarget
        fields = ["user", "month", "year", "target_clients", "approved_clients"]

    def validate(self, attrs):
        """Ensure month/year default values are applied if missing."""
        attrs.setdefault("month", date.today().month)
        attrs.setdefault("year", date.today().year)
        return attrs

    def create(self, validated_data):
        """Handle case where user is None (assign targets to all employees)."""
        user = validated_data.pop("user", None)  # Get user or None

        if user:  # Creating target for a specific employee
            target, _ = MonthlyTarget.objects.update_or_create(
                user=user, month=validated_data["month"], year=validated_data["year"],
                defaults={"target_clients": validated_data["target_clients"]}
            )
            return target
        else:  # Creating target for ALL employees
            employees = User.objects.filter(role="employee")
            targets = []
            for emp in employees:
                target, _ = MonthlyTarget.objects.update_or_create(
                    user=emp, month=validated_data["month"], year=validated_data["year"],
                    defaults={"target_clients": validated_data["target_clients"]}
                )
                targets.append(target)
            return targets  # Return a list when setting targets for all

    def to_representation(self, instance):
        """Ensure consistent output for multiple targets."""
        if isinstance(instance, list):
            return [super().to_representation(obj) for obj in instance]
        return super().to_representation(instance)
# class MonthlyTargetSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MonthlyTarget
#         fields = ["user", "month", "year", "target_clients"]
#         extra_kwargs = {
#             "user": {"required": False},   # Make user optional
#             "month": {"required": False},  # Auto-set in create method
#             "year": {"required": False},   # Auto-set in create method
#         }

#     def create(self, validated_data):
#         # Auto-set month and year
#         validated_data.setdefault("month", date.today().month)
#         validated_data.setdefault("year", date.today().year)

#         # If user is missing, raise an error
#         if "user" not in validated_data:
#             raise serializers.ValidationError({"user": "This field is required."})

#         return super().create(validated_data)


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "phone_number"]