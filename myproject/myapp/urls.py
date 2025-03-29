from django.urls import path
from .views import (
    ClientListCreateView, EmployeeClientUpdateView, ManagerClientUpdateView,
    EmployeeClientDetailsUpdateView,ClientApplicationView,UploadClientDocumentsView,
    GetClientDocumentsView,AttendanceListCreateView,MonthlyTargetView,EmployeeListView,
    EmployeeClientListView,EmployeeTargetView,
)
from .views import RegisterEmployeeView, LoginEmployeeView, ClientRetrieveView,ManagerPerformanceView
 



urlpatterns = [
    path('clients/', ClientListCreateView.as_view(), name='client-list-create'),
    path('clients/<int:pk>/', ClientRetrieveView.as_view(), name='client-retrieve'),

    path('clients/<int:pk>/update/', EmployeeClientUpdateView.as_view(), name='employee-client-update'),
    path('clients/<int:pk>/manager-update/', ManagerClientUpdateView.as_view(), name='manager-client-update'),
    path('clients/<int:pk>/details-update/', EmployeeClientDetailsUpdateView.as_view(), name='employee-client-details-update'),
    path("register/", RegisterEmployeeView.as_view(), name="register"),
    path("login/", LoginEmployeeView.as_view(), name="login"),
    # path("employee/clients/", EmployeeClientManageView.as_view(), name="employee-clients"),
    # path("employee/clients/<int:pk>/", EmployeeClientManageView.as_view(), name="employee-client-update"),
    path("client/apply/", ClientApplicationView.as_view(), name="client-apply"),
    path('upload-documents/<int:client_id>/', UploadClientDocumentsView.as_view(), name='upload-documents'),
    path('client-documents/<int:client_id>/', GetClientDocumentsView.as_view(), name='client-documents'),
    path('attendance/', AttendanceListCreateView.as_view(), name='attendance-list'),
    # path('manage/target/', MonthlyTargetView.as_view(), name='manage-target'),
    path("manage/employees/", EmployeeListView.as_view(), name="manage-employees"),
    path("manage/employees/<int:employee_id>/clients/", EmployeeClientListView.as_view(), name="employee-clients"),
     path("targets/", MonthlyTargetView.as_view(), name="set-target"),
    path("targets/my-performance/", EmployeeTargetView.as_view(), name="employee-performance"),
    path("targets/performance/", ManagerPerformanceView.as_view(), name="manager-employee-performance"),
]
