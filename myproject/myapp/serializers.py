from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, EmployeeClientDetails
from django.conf import settings

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
    aadhaar_front = serializers.SerializerMethodField()
    aadhaar_back = serializers.SerializerMethodField()
    cibil_report = serializers.SerializerMethodField()
    pan_card = serializers.SerializerMethodField()
    gas_bill = serializers.SerializerMethodField()

    def get_full_url(self, file_field):
        """Convert relative file path to full URL."""
        if file_field:
            request = self.context.get("request")
            return request.build_absolute_uri(settings.MEDIA_URL + str(file_field)) if request else f"{settings.MEDIA_URL}{file_field}"
        return None

    def get_aadhaar_front(self, obj):
        return self.get_full_url(obj.aadhaar_front)

    def get_aadhaar_back(self, obj):
        return self.get_full_url(obj.aadhaar_back)

    def get_cibil_report(self, obj):
        return self.get_full_url(obj.cibil_report)

    def get_pan_card(self, obj):
        return self.get_full_url(obj.pan_card)

    def get_gas_bill(self, obj):
        return self.get_full_url(obj.gas_bill)

    class Meta:
        model = EmployeeClientDetails
        fields = "__all__"