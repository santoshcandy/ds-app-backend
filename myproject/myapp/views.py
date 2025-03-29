from django.shortcuts import render
from rest_framework.permissions import BasePermission
# Create your views here.
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Client, EmployeeClientDetails
from .serializers import ClientSerializer, EmployeeClientDetailsSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User,Attendance,MonthlyTarget
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserSerializer
import random
from .serializers import EmployeeClientDetailsSerializer, AttendanceSerializer,MonthlyTargetSerializer,EmployeeSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError 
from datetime import date, datetime, time

# ✅ Generate JWT Token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# ✅ Employee & Manager Registration API
class RegisterEmployeeView(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response(
                {"message": "Registration successful", "tokens": tokens, "user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ✅ Employee & Manager Login API
class LoginEmployeeView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            phone_number = serializer.validated_data["phone_number"]
            dob = serializer.validated_data["dob"]
            role = serializer.validated_data["role"]
            password = serializer.validated_data["password"]

            user = User.objects.filter(email=email, phone_number=phone_number, dob=dob, role=role).first()

            if user and user.check_password(password):
                tokens = get_tokens_for_user(user)
                return Response(
                    {"message": "Login successful", "tokens": tokens, "user": UserSerializer(user).data},
                    status=status.HTTP_200_OK
                )
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class IsEmployee(BasePermission):
    """
    Custom permission: Only employees can access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'employee'
class IsManager(BasePermission):
    """Allows access only to managers."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager
# class IsManager(BasePermission):
#     """
#     Custom permission: Only managers can access.
#     """
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.role == 'manager'

# ✅ Create & View Clients (Employees & Managers)
class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter clients based on user role"""
        user = self.request.user
        
        if user.role == 'employee':  
            return Client.objects.filter(assigned_employee=user)  # Only assigned clients
        return Client.objects.all()  # Managers can view all clients

    def perform_create(self, serializer):
        """Assign an employee dynamically in API View"""
        client_type = serializer.validated_data.get('client_type', 'direct')  # Default to direct

        if client_type == 'direct':
            # 🚀 TODO: Add logic to assign an available employee automatically (if required)
            serializer.save()
        else:
            if self.request.user.role == 'employee':  # Ensure only employees are assigned
                serializer.save(assigned_employee=self.request.user)
            else:
                raise serializer.ValidationError({"error": "Only employees can be assigned to clients."})

# ✅ Employee: View & Update Only Their Clients


class EmployeeClientUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ClientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ✅ Correct way to check if the user is a manager
        if user.groups.filter(name="Manager").exists():  
            return Client.objects.all()  # Manager can update any client

        return Client.objects.filter(assigned_employee=user) 
     # Employee can update only assigned clients
# ✅ Manager: View & Update Any Client
class ManagerClientUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsManager]

# ✅ Employee & Manager: Update Employee Client Details (CIBIL, Aadhaar, PAN, etc.)
class EmployeeClientDetailsUpdateView(generics.RetrieveUpdateAPIView):
    queryset = EmployeeClientDetails.objects.all()
    serializer_class = EmployeeClientDetailsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Both Employees & Managers can update


 
class ClientRetrieveView(generics.RetrieveAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]  # Ensure user is authenticated

    def get_queryset(self):
        user = self.request.user
        if user.role == "employee":
            return Client.objects.filter(assigned_employee=user)  # Show only assigned clients
        elif user.role == "manager":
            return Client.objects.all()  # Manager can see all clients
        return Client.objects.none()
  
 
class ClientApplicationView(APIView):
    permission_classes = [permissions.AllowAny]  # No authentication required

    def post(self, request):
        """Client can apply without login. The system will auto-assign an employee if not provided."""
        required_fields = [
            "name", "contact_number", "father_name", "mother_name",
            "qualifications", "married_status", "current_address",
            "landmark", "years_at_address", "gmail", "office_name",
            "office_address", "designation", "department",
            "current_experience", "overall_experience",
            "reference_name_1", "reference_number_1",
            "reference_name_2", "reference_number_2",
            "expected_loan_amount", "loan_purpose"
        ]

        # ✅ Debug: Print received data
        print("Received Data:", request.data)

        # ✅ Check if all required fields exist
        missing_fields = [key for key in required_fields if key not in request.data]
        if missing_fields:
            return Response(
                {"error": f"Missing fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Extract assigned_employee_id
        assigned_employee_id = request.data.get("assigned_employee")

        if assigned_employee_id and assigned_employee_id != "null":
            # If an employee ID is provided, validate it
            assigned_employee = User.objects.filter(id=assigned_employee_id, role="employee").first()
            if not assigned_employee:
                return Response(
                    {"error": "Invalid assigned employee ID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            client_type = "employee_client"
        else:
            # Auto-assign employee using round-robin method
            employees = User.objects.filter(role="employee").annotate(client_count=Count("clients")).order_by("client_count")
            assigned_employee = employees.first() if employees.exists() else None
            client_type = "direct"

        # ✅ Prepare data for serializer
        data = request.data.copy()
        data["client_type"] = client_type
        data["assigned_employee"] = assigned_employee.id if assigned_employee else None  # Fix

        # ✅ Validate and save the data
        serializer = ClientSerializer(data=data)
        if serializer.is_valid():
            serializer.save(assigned_employee=assigned_employee)
            return Response(
                {
                    "message": "Client application submitted successfully",
                    "client": serializer.data,
                    "assigned_employee": assigned_employee.email if assigned_employee else "Not assigned yet"
                },
                status=status.HTTP_201_CREATED
            )

        # ✅ Log and return exact serializer errors
        print("Serializer Errors:", serializer.errors)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class SendApprovalRequestView(APIView):
    """
    Employee sends client details to Manager (MD) for loan approval.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEmployee]  # Only employees can send requests

    def post(self, request, client_id):
        try:
            client = Client.objects.get(id=client_id, assigned_employee=request.user)

            # Ensure only employee-registered clients are sent for approval
            if client.client_type != "employee_registered":
                return Response({"error": "Only employee-registered clients can be sent for approval."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch additional client details
            try:
                extra_details = client.extra_details
            except ObjectDoesNotExist:
                return Response({"error": "Client details not found. Please complete all fields before sending approval."}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Check Required Fields
            required_fields = ["cibil_score", "aadhaar_front", "aadhaar_back", "cibil_report", "pan_card"]
            missing_fields = [field for field in required_fields if not getattr(extra_details, field)]

            if missing_fields:
                return Response({"error": f"Missing fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Mark client as pending approval
            client.approval_status = "pending"
            client.save()

            # ✅ Get Employee (Sender) Details
            employee = request.user  # Employee sending the request

            return Response(
                {
                    "message": "Approval request sent to Manager (MD).",
                    "client_details": {
                        "client_id": client.id,
                        "client_name": client.name,
                        "contact_number": client.contact_number,
                        "email": client.gmail,
                        "address": client.current_address,
                        "loan_amount": client.expected_loan_amount,
                        "loan_purpose": client.loan_purpose,
                        "status": client.approval_status
                    },
                    "employee_details": {
                        "employee_id": employee.id,
                        "employee_name": employee.name,
                        "email": employee.email,
                        "phone_number": employee.phone_number,
                        "role": employee.role
                    }
                },
                status=status.HTTP_200_OK
            )

        except Client.DoesNotExist:
            return Response({"error": "Client not found or not assigned to you."}, status=status.HTTP_404_NOT_FOUND)
class UploadClientDocumentsView(APIView):
    parser_classes = [MultiPartParser, FormParser]  # ✅ Handles file uploads
    permission_classes = [IsAuthenticated]  # ✅ Requires JWT authentication

    def patch(self, request, client_id):
        print("🔴 DEBUG: Received Data -->", request.data)  # ✅ Print form fields
        print("🔴 DEBUG: Received FILES -->", request.FILES)  # ✅ Print uploaded files

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)

        extra_details, created = EmployeeClientDetails.objects.get_or_create(client=client)

        serializer = EmployeeClientDetailsSerializer(extra_details, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            print("✅ DEBUG: Saved successfully")
            return Response({
                "message": "Documents uploaded successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        print("❌ DEBUG: Serializer Errors -->", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetClientDocumentsView(APIView):
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, client_id):
        try:
            client_docs = EmployeeClientDetails.objects.get(client_id=client_id)
            serializer = EmployeeClientDetailsSerializer(client_docs)
            return Response(serializer.data, status=200)
        except EmployeeClientDetails.DoesNotExist:
            return Response({"error": "No documents found"}, status=404)
        

# sriram attdendancde code
 

 


class AttendanceListCreateView(generics.ListCreateAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            return Attendance.objects.all()  # Manager can see all records
        return Attendance.objects.filter(user=user)  # Employee sees only their own records

    def perform_create(self, serializer):
        user = self.request.user
        today = date.today()
        now = datetime.now().time()  # Get current time
        cutoff_time = time(11, 0)  # 11:00 AM cutoff

        # Check if attendance for today already exists
        if Attendance.objects.filter(user=user, date=today).exists():
            raise ValidationError("You have already marked attendance for today.")

        # If the current time is past 11:00 AM, mark as "Absent" automatically
        status_value = "Absent" if now > cutoff_time else serializer.validated_data.get("status", "Present")

        serializer.save(user=user, date=today, status=status_value)  # Save attendance with appropriate status


class MonthlyTargetView(generics.ListCreateAPIView):
    queryset = MonthlyTarget.objects.all()
    serializer_class = MonthlyTargetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "manager":
            raise ValidationError("Only managers can set targets.")

        data = self.request.data
        month, year = date.today().month, date.today().year  # ✅ Get default month and year

        if "user" in data and data["user"]:  
            # ✅ Set target for a specific employee
            try:
                employee = User.objects.get(id=data["user"], role="employee")
            except User.DoesNotExist:
                raise ValidationError("Invalid employee ID.")

            target, created = MonthlyTarget.objects.update_or_create(
                user=employee, month=month, year=year,
                defaults={"target_clients": data["target_clients"]}
            )

            return Response({"message": f"Target {'updated' if not created else 'set'} for {employee.username}"})

        else:
            # ✅ Set target for all employees
            employees = User.objects.filter(role="employee")
            if not employees:
                return Response({"message": "No employees found."}, status=400)

            for emp in employees:
                MonthlyTarget.objects.update_or_create(
                    user=emp, month=month, year=year,
                    defaults={"target_clients": data["target_clients"]}
                )

            return Response({"message": "Targets updated for all employees"})
class UpdateMonthlyTargetView(APIView):
    """Allow managers to update an existing employee's target."""
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, target_id):
        user = request.user
        if user.role != "manager":
            raise ValidationError("Only managers can update targets.")

        try:
            target = MonthlyTarget.objects.get(id=target_id)
        except MonthlyTarget.DoesNotExist:
            return Response({"error": "Target not found"}, status=404)

        target_clients = request.data.get("target_clients")
        if target_clients is not None:
            target.target_clients = target_clients
            target.save()
            return Response({"message": f"Target updated for {target.user.username}"})
        else:
            return Response({"error": "target_clients field is required"}, status=400)
      
class EmployeeTargetView(generics.ListAPIView):
    """
    API for employees to view their current target & performance history.
    """
    serializer_class = MonthlyTargetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != "employee":
            raise ValidationError("Only employees can access this data.")

        # Get last 5 months data
        today = date.today()
        min_date = today.replace(month=max(1, today.month - 5))

        return MonthlyTarget.objects.filter(
            user=user,
            year__gte=min_date.year,
            month__gte=min_date.month
        ).order_by("-year", "-month")  # Show latest first


class EmployeePerformanceView(APIView):
    """Get employee performance history with correct completion count."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user  # Logged-in employee
        today = date.today()
        current_month, current_year = today.month, today.year

        # Get current month's target
        current_target = MonthlyTarget.objects.filter(user=user, month=current_month, year=current_year).first()

        # Get last 5 months' history
        five_months_ago = today - timedelta(days=150)  # Approx. 5 months
        past_targets = MonthlyTarget.objects.filter(
            user=user, 
            year__gte=five_months_ago.year,
            month__gte=five_months_ago.month
        ).order_by("-year", "-month")[:5]

        # Count approved clients from Client model
        approved_clients = Client.objects.filter(
            assigned_employee=user, 
            approval_status="approved"
        ).count()

        # Calculate completion percentage
        def calculate_completion(target):
            if target and target.target_clients > 0:
                return f"{(target.approved_clients / target.target_clients) * 100:.2f}%"
            return "0%"

        # Format response
        response_data = {
            "employee": user.username,
            "current_month": {
                "month": current_month,
                "year": current_year,
                "target_clients": current_target.target_clients if current_target else 0,
                "approved_clients": approved_clients,
                "completion": calculate_completion(current_target)
            },
            "last_5_months": [
                {
                    "month": target.month,
                    "year": target.year,
                    "target_clients": target.target_clients,
                    "approved_clients": target.approved_clients,
                    "completion": calculate_completion(target)
                } for target in past_targets
            ]
        }

        return Response(response_data)

 

class ManagerPerformanceView(generics.ListAPIView):
    """
    Managers can view performance of all employees or a specific employee.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role != "manager":
            raise PermissionDenied("Only managers can view performance data.")

        employee_id = request.query_params.get("employee_id")

        if employee_id:
            return self.get_specific_employee_performance(employee_id)
        return self.get_all_employees_performance()

    def get_specific_employee_performance(self, employee_id):
        try:
            employee = User.objects.get(id=employee_id, role="employee")
        except User.DoesNotExist:
            raise NotFound("Employee not found.")

        today = date.today()
        last_five_months = [(today.month - i, today.year) for i in range(5)]

        targets = MonthlyTarget.objects.filter(
            user=employee,
            month__in=[m[0] for m in last_five_months],
            year__in=[m[1] for m in last_five_months]
        )

        performance_data = [
            {
                "month": target.month,
                "year": target.year,
                "target_clients": target.target_clients,
                "approved_clients": Client.objects.filter(
                    assigned_employee=employee,
                    approval_status="approved",
                    created_at__month=target.month,
                    created_at__year=target.year
                ).count(),  # ✅ Dynamically fetch approved clients
                "completion": f"{(Client.objects.filter(
                    assigned_employee=employee,
                    approval_status='approved',
                    created_at__month=target.month,
                    created_at__year=target.year
                ).count() / target.target_clients * 100) if target.target_clients else 0:.2f}%"
            }
            for target in targets
        ]

        return Response({
            "employee": employee.username,
            "performance": performance_data
        })

    def get_all_employees_performance(self):
        today = date.today()
        last_five_months = [(today.month - i, today.year) for i in range(5)]

        employees = User.objects.filter(role="employee")
        performance_data = []

        for employee in employees:
            targets = MonthlyTarget.objects.filter(
                user=employee,
                month__in=[m[0] for m in last_five_months],
                year__in=[m[1] for m in last_five_months]
            )

            employee_performance = {
                "employee": employee.username,
                "performance": [
                    {
                        "month": target.month,
                        "year": target.year,
                        "target_clients": target.target_clients,
                        "approved_clients": Client.objects.filter(
                            assigned_employee=employee,
                            approval_status="approved",
                            created_at__month=target.month,
                            created_at__year=target.year
                        ).count(),  # ✅ Dynamically fetch approved clients
                        "completion": f"{(Client.objects.filter(
                            assigned_employee=employee,
                            approval_status='approved',
                            created_at__month=target.month,
                            created_at__year=target.year
                        ).count() / target.target_clients * 100) if target.target_clients else 0:.2f}%"
                    }
                    for target in targets
                ]
            }

            performance_data.append(employee_performance)

        return Response(performance_data)

    
class EmployeeListView(generics.ListAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            return User.objects.filter(role="employee")  # Managers see all employees
        return User.objects.none()  # Others see nothing


class EmployeeClientListView(generics.ListAPIView):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'manager':
            employee_id = self.kwargs.get("employee_id")
            return Client.objects.filter(assigned_employee_id=employee_id)  # Filter clients by employee
        return Client.objects.none()  # Others see nothing