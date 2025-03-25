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
from .models import User
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserSerializer
import random
from .serializers import EmployeeClientDetailsSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated



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
                raise serializers.ValidationError({"error": "Only employees can be assigned to clients."})

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
    """
    Upload documents for a specific client.
    """
    parser_classes = [MultiPartParser, FormParser]  # Handles file uploads
    permission_classes = [IsAuthenticated]
    def post(self, request, client_id):
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get or create EmployeeClientDetails entry
        extra_details, created = EmployeeClientDetails.objects.get_or_create(client=client)

        serializer = EmployeeClientDetailsSerializer(extra_details, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Documents uploaded successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

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