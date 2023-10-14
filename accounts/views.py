import os
from accounts.resources import WorkLogResource
from project.models import Project
import sales
from django.contrib.auth import login, logout
from accounts import models
from accounts.models import NotificationPrivilege, User, Role, WorkLog, MaterialLog, AssetLog, Holiday, OTCalculation, Privilege, UserCert, UserAddress, UserItemIssued, UserItemTool
from django.urls import reverse_lazy
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import FormView, RedirectView
from django.http import HttpResponse, HttpResponseRedirect, request
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from accounts.forms import SingupForm
from django.views.generic.list import ListView
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
import random
import string
from django.db.models import Q
from sales.decorater import ajax_login_required, admin_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import IntegrityError
from cities_light.models import Country
from dateutil import parser as date_parser
import pytz
from django.shortcuts import render, redirect
import json
import datetime
from accounts.email import send_active_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_text
from notifications import models as Notification
from notifications.signals import notify
import pandas as pd

# Create your views here.

class LoginView(FormView):
    form_class = AuthenticationForm
    template_name = "accounts/sign-in.html"
    
    def get_success_url(self):
        return reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())

        return super(LoginView, self).form_valid(form)

class LogoutView(RedirectView):
    url = '/login/'

    def get(self, request, *args, **kwargs):
        logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

class SignupView(CreateView):
    model = User
    form_class = SingupForm
    template_name = 'accounts/sign-up.html'
    success_url = reverse_lazy('view_login')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object
        form = self.form_class(request.POST)
        email = request.POST.get('email')


        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.email= email
            new_user.save()
            
            return HttpResponseRedirect(self.get_success_url())

        else:

            return self.render_to_response(self.get_context_data(form=form))


#Users part =================================
@method_decorator(login_required, name='dispatch')
@method_decorator(admin_required, name='dispatch')
class UsersList(ListView):
    model = User
    template_name = "accounts/users-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all().exclude(is_staff=True)
        context['nrics'] = User.objects.exclude(nric=None).order_by('nric').values('nric').distinct()
        context['empids'] = User.objects.exclude(empid=None).order_by('empid').values('empid').distinct()
        context['roles'] = Role.objects.all()

        return context

@ajax_login_required
def ajax_users(request):
    if request.method == "POST":
        users = User.objects.all().exclude(is_staff=True)

        return render(request, 'accounts/ajax-all-users.html', {'users': users})

@ajax_login_required
def ajax_users_filter(request):
    if request.method == "POST":
        search_empno = request.POST.get('search_empno')
        search_nric = request.POST.get('search_nric')
        search_role = request.POST.get('search_role')
        if search_empno != "" and search_nric == "" and search_role == "":
            users = User.objects.filter(empid__iexact=search_empno)

        elif search_empno != "" and search_nric != "" and search_role == "":
            users = User.objects.filter(empid__iexact=search_empno, nric__iexact=search_nric)
        
        elif search_empno != "" and search_nric != "" and search_role != "":
            users = User.objects.filter(empid__iexact=search_empno, nric__iexact=search_nric, role__iexact=search_role)

        elif search_empno == "" and search_nric != "" and search_role == "":
            users = User.objects.filter(nric__iexact=search_nric)

        elif search_empno == "" and search_nric != "" and search_role != "":
            users = User.objects.filter(nric__iexact=search_nric, role__iexact=search_role)

        elif search_empno == "" and search_nric == "" and search_role != "":
            users = User.objects.filter(role__iexact=search_role)

        elif search_empno != "" and search_nric == "" and search_role != "":
            users = User.objects.filter(empid__iexact=search_empno,role__iexact=search_role)

        return render(request, 'accounts/ajax-all-users.html', {'users': users})

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_required, name='dispatch')
class UsersConfiguration(ListView):
    model = User
    template_name = "accounts/user-configuration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles = Role.objects.all().order_by('name')
        role_lists = []
        users_classify = [[]]
        users_classify.clear()
        for role in roles:
            temp_data = []
            role_lists.append(role.name)
            classify = User.objects.exclude(is_staff=True).filter(role__iexact=role.name)
            temp_data.append(role.name)
            temp_data.append(classify)
            users_classify.append(temp_data)
        context['users_classify'] = users_classify
        context['role_lists'] = role_lists
        
        return context

@method_decorator(login_required, name='dispatch')
class NotificationConfiguration(ListView):
    model = User
    template_name = "accounts/notification-configuration.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        roles = Role.objects.all().order_by('name')
        role_lists = []
        notification_classify = [[]]
        notification_classify.clear()
        for role in roles:
            temp_data = []
            role_lists.append(role.name)
            classify_notification = User.objects.exclude(is_staff=True).filter(role__iexact=role.name)
            temp_data.append(role.name)
            temp_data.append(classify_notification)
            notification_classify.append(temp_data)
        context['notification_classify'] = notification_classify
        context['role_lists'] = role_lists

        return context

@ajax_login_required
def ajaxaddRole(request):
    if request.method == "POST":
        role_name = request.POST.get('role_name')

        if Role.objects.filter(name__iexact=role_name).exists():
            return JsonResponse({
                "status": "Error",
                "messages": "Already this role is existed!"
            })

        else:
            Role.objects.create(
                name=role_name
            )
            #notification send
            sender = request.user
            description = request.user.username +  ' - was created New Role ' + role_name
            for receiver in User.objects.all():
                if receiver.notificationprivilege.usergroup_created:
                    notify.send(sender, recipient=receiver, verb='Message', level="success", description=description)
            return JsonResponse({
                    "status": "Success",
                    "messages": "Role information added!"
                })

def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

@ajax_login_required
def newUser(request):
    if request.method == "POST":
        empno = request.POST.get('empno')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        nationality = request.POST.get('nationality')
        nric = request.POST.get('nric')
        role = request.POST.get('role')
        phone = request.POST.get('phone')

        userid = request.POST.get('userid')
        password = make_password(id_generator())

        if userid == "-1":
            try:
                if User.objects.filter(empid__iexact=empno).exists():
                    return JsonResponse({
                        "status": "Error",
                        "messages": "Already Emp No is existed!"
                    })
                else:
                    user = User.objects.create(
                        empid=empno,
                        first_name=firstname,
                        last_name=lastname,
                        nationality=nationality,
                        nric=nric,
                        role=role,
                        phone=phone,
                        password=password,
                        is_active=False,
                        username=firstname + lastname
                    )
                    Privilege.objects.create(
                        user_id=user.id,
                        sales_summary = "Only View",
                        sales_report = "Only View",
                        proj_summary = "Only View",
                        proj_ot = "Only View",
                        prof_summary = "Only View",
                        invent_material = "Only View"
                    )
                    NotificationPrivilege.objects.create(
                        user_id=user.id,
                        project_no_created=True,
                        project_status=True,
                        project_end=2,
                        tbm_no_created=True,
                        inventory_item_deleted=True,
                        stock_equal_restock=True,

                        do_status=True,
                        service_status=True,
                        pc_status=True,
                        usergroup_created=True,
                        user_no_created=True,
                        claim_no_created=True,
                        contract_end=3,
                        hardware_end=3,
                        schedule_end=2,
                        password_change=True
                    )
                    #notification send
                    sender = request.user
                    description = 'User Emp No : ' + user.empid +  ' - New User was created by ' + request.user.username
                    for receiver in User.objects.all():
                        if receiver.notificationprivilege.user_no_created:
                            notify.send(sender, recipient=receiver, verb='Message', level="success", description=description)
                    return JsonResponse({
                        "status": "Success",
                        "messages": "New User information added!",
                        "newUserId": user.id,
                        "method": "add"
                    })
            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

        else:
            try:
                user = User.objects.get(id=userid)
                user.empid=empno
                user.first_name=firstname
                user.last_name=lastname
                user.nationality=nationality
                user.nric=nric
                user.role=role
                user.phone=phone
                user.password=password
                user.username=firstname + lastname
                user.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "User information Updated!",
                    "newUserId": user.id,
                    "method": "update"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Updating Error!"
                })


@method_decorator(login_required, name='dispatch')
class UserDetailView(DetailView):
    model = User
    template_name="accounts/userdetail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        #context['user'] = User.objects.get(id=content_pk)
        current_user = User.objects.get(id=content_pk)
        context['countrys'] = Country.objects.all()
        context['roles'] = Role.objects.all()
        context['certificates'] = UserCert.objects.filter(emp_id__iexact=current_user.username)
        context['issuedtools'] = UserItemTool.objects.filter(emp_id__iexact=current_user.username)
        context['selected_user'] = content_pk
        context['current_user'] = current_user
        if UserAddress.objects.filter(emp_id_id=content_pk).exists():
            context['useraddress'] = UserAddress.objects.get(emp_id_id=content_pk)
        else:
            context['useraddress'] = []

        context['issueditems'] = UserItemIssued.objects.filter(empid__iexact=current_user.empid)
        context['issueusers'] = User.objects.filter(Q(role__icontains='Managers') | Q(role__icontains='Engineers') | Q(is_staff=True))
        return context

@ajax_login_required
def UpdateUser(request):
    if request.method == "POST":
        
        empno = request.POST.get('empno')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        nationality = request.POST.get('nationality')
        nric = request.POST.get('nric')
        role = request.POST.get('role')
        phone = request.POST.get('phone')
        wp_type = request.POST.get('wp_type')
        wp_no = request.POST.get('wp_no')
        wp_expiry = request.POST.get('wp_expiry')
        passport_no = request.POST.get('passport_no')
        passport_expiry = request.POST.get('passport_expiry')
        email = request.POST.get('email')
        dob = request.POST.get('dob')
        address = request.POST.get('address')
        unit = request.POST.get('unit')
        postalcode = request.POST.get('postalcode')
        country = request.POST.get('country')
        username = request.POST.get('username')
        basic_salary = request.POST.get('basic_salary')
        password = request.POST.get('password')
        userid = request.POST.get('userid')
        pincode = request.POST.get('pincode')
        fcm_token = request.POST.get('fcm_token')
        passwordbox = password
        password = make_password(password)
        try:
            user = User.objects.get(id=userid)
            
            user.empid=empno
            user.first_name=firstname
            user.last_name=lastname
            user.nationality=nationality
            user.nric=nric
            user.role=role
            user.phone=phone
            user.password=password
            user.password_box=passwordbox
            user.basic_salary=basic_salary
            user.username=username
            user.dob=dob
            user.email=email
            user.passport_expiry=passport_expiry
            user.passport_no=passport_no
            user.is_active = True
            user.wp_type=wp_type
            user.wp_no=wp_no
            user.wp_expiry=wp_expiry

            user.pincode=pincode
            user.fcm_token=fcm_token
            user.save()
            if UserAddress.objects.filter(emp_id=user.id).exists():
                useraddress = UserAddress.objects.get(emp_id=user.id)
                useraddress.address=address
                useraddress.unit=unit
                useraddress.postal_code=postalcode
                useraddress.country_id=country
                useraddress.save()
            else:
                UserAddress.objects.create(
                    address=address,
                    unit=unit,
                    postal_code=postalcode,
                    country_id=country,
                    emp_id_id=user.id
                )
            if user.is_active != True:
                mail_subject = "YOU'RE INVITED TO BECOME A FELLOW MEMBER OF ERP SOLUTION"
                mail_context = {
                    'email_title': "YOU'RE INVITED TO BECOME A FELLOW MEMBER OF",
                    'email_body': "Utiliza este email para activar tu cuenta, y empezar a trabajar con nuestra plataforma.",
                    'user': user,
                    'site_url': request._current_scheme_host,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                }
                send_active_mail(mail_subject, email_template_name=None,context=mail_context, to_email=[user.email],html_email_template_name='email.html')

            return JsonResponse({
                "status": "Success",
                "messages": "New User information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@method_decorator(login_required, name='dispatch')
class WorkLogList(ListView):
    model = WorkLog
    template_name = "accounts/worklog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emp_nos'] = WorkLog.objects.exclude(emp_no=None).order_by('emp_no').values('emp_no').distinct()
        context['emp_users'] = User.objects.all()
        context['projects'] = Project.objects.order_by('proj_id').values('proj_id').distinct()
        context['date_years'] = list(set([d.checkin_time.year for d in WorkLog.objects.all()]))
        current_year = datetime.datetime.today().year
        if current_year in list(set([d.start_date.year for d in Project.objects.all()])):
            context['exist_current_year'] = True
        else:
            context['exist_current_year'] = False
        return context

@ajax_login_required
def ajax_worklog(request):
    if request.method == "POST":
        current_year = datetime.datetime.today().year
        current_month = datetime.datetime.today().month
        worklogs = WorkLog.objects.filter(checkin_time__year=current_year, checkin_time__month=current_month)

        return render(request, 'accounts/ajax-worklog.html', {'worklogs': worklogs})

@ajax_login_required
def ajax_export_worklog(request):
    resource = WorkLogResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="work-log.csv"'
    return response

def ajax_import_worklog(request):
    
    if request.method == 'POST':
        org_column_names = ['emp_no', 'project_name', 'projectcode', 'checkin_time', 'checkin_lat', 'checkin_lng', 'checkout_time', 'checkout_lat', 'checkout_lng']
        
        csv_file = request.FILES['file']
        contents = csv_file.read().decode('UTF-8')
        path = "temp.csv"
        f = open(path,'w')
        f.write(contents)
        f.close()

        df = pd.read_csv(path)    
        df.fillna("", inplace=True)
        column_names = list(df)

        if len(column_names) == 1:
            df = pd.read_csv(path, delimiter = ';', decimal = ',', encoding = 'utf-8')    
            df.fillna("", inplace=True)
            column_names = list(df)
        
        dif_len = len(list(set(org_column_names) - set(column_names)))

        if dif_len == 0:
            record_count = len(df.index)
            success_record = 0
            failed_record = 0
            exist_record = 0
            for index, row in df.iterrows():
                exist_count = WorkLog.objects.filter(emp_no=row["emp_no"]).count()
                if exist_count == 0:
                    try:
                        worklog = WorkLog(
                            emp_no=row["emp_no"],
                            project_name=row["project_name"],
                            projectcode=row["projectcode"],
                            checkin_time=datetime.datetime.strptime(row["checkin_time"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc),
                            checkin_lat=row["checkin_lat"],
                            checkin_lng=row["checkin_lng"],
                            checkout_time=datetime.datetime.strptime(row["checkout_time"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc),
                            checkout_lat=row["checkout_lat"],
                            checkout_lng=row["checkout_lng"],
                        )
                        worklog.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        worklog = WorkLog.objects.filter(emp_no=row["emp_no"])[0]
                        worklog.emp_no = row["emp_no"]
                        worklog.project_name = row["project_name"]
                        worklog.projectcode=str(row["projectcode"])
                        worklog.checkin_time=datetime.datetime.strptime(row["checkin_time"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                        worklog.checkin_lat=row["checkin_lat"]
                        worklog.checkin_lng=str(row["checkin_lng"])
                        worklog.checkout_time=datetime.datetime.strptime(row["checkout_time"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                        worklog.checkout_lat=row["checkout_lat"]
                        worklog.checkout_lng=row["checkout_lng"]
                        worklog.save()
                        
                        exist_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
            os.remove(path)
            return JsonResponse({'status':'true','error_code':'0', 'total': record_count, 'success': success_record, 'failed': failed_record, 'exist': exist_record})
        else:
            os.remove(path)
            # column count is not equals
            return JsonResponse({'status':'false','error_code':'1'})
    return HttpResponse("Ok")

@ajax_login_required
def ajax_get_project_name(request):
    if request.method == "POST":
        project_code = request.POST.get('project_code')
        if Project.objects.filter(proj_id__iexact=project_code).exists():
            project= Project.objects.filter(proj_id__iexact=project_code).order_by('-proj_id')[0]
            data = {
                "status": "exist",
                "project_name": project.proj_name,
                "latitude": project.latitude,
                "longitude": project.longitude
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def ajax_worklog_filter(request):
    if request.method == "POST":
        daterange = request.POST.get('daterange')
        search_empno = request.POST.get('search_empno')
        search_year = request.POST.get('search_year')
        if daterange != "":
            startdate = datetime.datetime.strptime(daterange.split('-')[0].strip(),'%Y.%m.%d %H:%M').replace(tzinfo=pytz.utc)
            enddate = datetime.datetime.strptime(daterange.split('-')[1].strip(), '%Y.%m.%d %H:%M').replace(tzinfo=pytz.utc)
        if search_year:
            if search_empno != "" and daterange != "":
                worklogs = WorkLog.objects.filter(emp_no__iexact=search_empno, checkin_time__gte=startdate, checkout_time__lte=enddate)
            elif search_empno != "" and daterange == "":
                worklogs = WorkLog.objects.filter(emp_no__iexact=search_empno)
            elif search_empno == "" and daterange != "":
                worklogs = WorkLog.objects.filter(checkin_time__gte=startdate, checkout_time__lte=enddate)
            elif search_empno == "" and daterange == "":
                worklogs = WorkLog.objects.filter(checkin_time__iso_year=search_year)
        else:
            if search_empno != "" and daterange != "":
                worklogs = WorkLog.objects.filter(emp_no__iexact=search_empno, checkin_time__gte=startdate, checkout_time__lte=enddate)
            elif search_empno != "" and daterange == "":
                worklogs = WorkLog.objects.filter(emp_no__iexact=search_empno)
            elif search_empno == "" and daterange != "":
                worklogs = WorkLog.objects.filter(checkin_time__gte=startdate, checkout_time__lte=enddate)

        return render(request, 'accounts/ajax-worklog.html', {'worklogs': worklogs})

@ajax_login_required
def worklogadd(request):
    if request.method == "POST":
        emp_no = request.POST.get('emp_no')
        project_code = request.POST.get('project_code')
        project_name = request.POST.get('project_name')
        checkin_time = request.POST.get('checkin_time')
        checkin_lat = request.POST.get('checkin_lat')
        checkin_lng = request.POST.get('checkin_lng')
        checkout_time = request.POST.get('checkout_time')
        checkout_lat = request.POST.get('checkout_lat')
        checkout_lng = request.POST.get('checkout_lng')
        worklogid = request.POST.get('worklogid')
        if worklogid == "-1":
            try:
                WorkLog.objects.create(
                    emp_no=emp_no,
                    project_name=project_name,
                    projectcode=project_code,
                    checkin_time=date_parser.parse(checkin_time).replace(tzinfo=pytz.utc),
                    checkin_lat=checkin_lat,
                    checkin_lng=checkin_lng,
                    checkout_time=date_parser.parse(checkout_time).replace(tzinfo=pytz.utc),
                    checkout_lat=checkout_lat,
                    checkout_lng=checkout_lng
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "WorkLog information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                worklog = WorkLog.objects.get(id=worklogid)
                worklog.emp_no=emp_no
                worklog.project_name = project_name
                worklog.projectcode = project_code
                worklog.checkin_time = date_parser.parse(checkin_time).replace(tzinfo=pytz.utc)
                worklog.checkin_lat = checkin_lat
                worklog.checkin_lng = checkin_lng
                worklog.checkout_time = date_parser.parse(checkout_time).replace(tzinfo=pytz.utc)
                worklog.checkout_lat = checkout_lat
                worklog.checkout_lng = checkout_lng
                worklog.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "WorkLog information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def worklogdelete(request):
    if request.method == "POST":
        worklogid = request.POST.get('worklogid')
        worklog = WorkLog.objects.get(id=worklogid)
        worklog.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getWorklog(request):
    if request.method == "POST":
        worklogid = request.POST.get('worklogid')
        worklog = WorkLog.objects.get(id=worklogid)
        data = {
            'emp_no': worklog.emp_no,
            'project_name': worklog.project_name,
            'project_code': worklog.projectcode,
            'checkin_time': worklog.checkin_time.strftime('%d %b, %Y %H:%M'),
            'checkin_lat': worklog.checkin_lat,
            'checkin_lng': worklog.checkin_lng,
            'checkout_time': worklog.checkout_time.strftime('%d %b, %Y %H:%M'),
            'checkout_lat': worklog.checkout_lat,
            'checkout_lng': worklog.checkout_lng,

        }
        return JsonResponse(json.dumps(data), safe=False)


@method_decorator(login_required, name='dispatch')
class MateriallogList(ListView):
    model = MaterialLog
    template_name = "accounts/materiallog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emp_nos'] = MaterialLog.objects.exclude(emp_no=None).order_by('emp_no').values('emp_no').distinct()
        context['materialcodes'] = MaterialLog.objects.exclude(material_code=None).order_by('material_code').values('material_code').distinct()
        context['materialnames'] = MaterialLog.objects.exclude(project_name=None).order_by('project_name').values('project_name').distinct()
        return context

@ajax_login_required
def ajax_materiallog(request):
    if request.method == "POST":
        materiallogs = MaterialLog.objects.all()

        return render(request, 'accounts/ajax-materiallog.html', {'materiallogs': materiallogs})

@ajax_login_required
def ajax_materiallog_filter(request):
       
    if request.method == "POST":
        search_empno = request.POST.get('search_empno')
        search_name = request.POST.get('search_name')
        search_code = request.POST.get('search_code')
        if search_empno != "" and search_name == "" and search_code == "":
            materiallogs = MaterialLog.objects.filter(emp_no__iexact=search_empno)

        elif search_empno != "" and search_name != "" and search_code == "":
            materiallogs = MaterialLog.objects.filter(emp_no__iexact=search_empno, project_name__iexact=search_name)
        
        elif search_empno != "" and search_name != "" and search_code != "":
            materiallogs = MaterialLog.objects.filter(emp_no__iexact=search_empno, project_name__iexact=search_name, material_code__iexact=search_code)

        elif search_empno == "" and search_name != "" and search_code == "":
            materiallogs = MaterialLog.objects.filter(project_name__iexact=search_name)

        elif search_empno == "" and search_name != "" and search_code != "":
            materiallogs = MaterialLog.objects.filter(material_code__iexact=search_code, project_name__iexact=search_name)

        elif search_empno == "" and search_name == "" and search_code != "":
            materiallogs = MaterialLog.objects.filter(material_code__iexact=search_code)

        elif search_empno != "" and search_name == "" and search_code != "":
            materiallogs = MaterialLog.objects.filter(emp_no__iexact=search_empno,material_code__iexact=search_code)

        return render(request, 'accounts/ajax-materiallog.html', {'materiallogs': materiallogs})

@ajax_login_required
def materiallogadd(request):
    if request.method == "POST":
        project_name = request.POST.get('project_name')
        emp_no = request.POST.get('emp_no')
        material_code = request.POST.get('material_code')
        material_out = request.POST.get('material_out')
        comment = request.POST.get('comment')
        date_time = request.POST.get('date_time')
        materiallogid = request.POST.get('materiallogid')
        if materiallogid == "-1":
            try:
                MaterialLog.objects.create(
                    project_name=project_name,
                    emp_no=emp_no,
                    material_code=material_code,
                    material_out=material_out,
                    comment=comment,
                    date_time=date_time
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Materiallog information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                materiallog = MaterialLog.objects.get(id=materiallogid)
                materiallog.project_name = project_name
                materiallog.emp_no = emp_no
                materiallog.material_code = material_code
                materiallog.material_out = material_out
                materiallog.comment = comment
                materiallog.date_time = date_time
                materiallog.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "MaterialLog information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def materiallogdelete(request):
    if request.method == "POST":
        materiallogid = request.POST.get('materiallogid')
        materiallog = MaterialLog.objects.get(id=materiallogid)
        materiallog.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getMateriallog(request):
    if request.method == "POST":
        materiallogid = request.POST.get('materiallogid')
        materiallog = MaterialLog.objects.get(id=materiallogid)
        data = {
            'emp_no': materiallog.emp_no,
            'material_code': materiallog.material_code,
            'project_name': materiallog.project_name,
            'comment': materiallog.material_out,
            'comment': materiallog.comment,
            'date_time': materiallog.date_time.strftime('%d %b, %Y %H:%M')

        }
        return JsonResponse(json.dumps(data), safe=False)

@method_decorator(login_required, name='dispatch')
class AssetLogList(ListView):
    model = AssetLog
    template_name = "accounts/assetlog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emp_nos'] = AssetLog.objects.exclude(emp_no=None).order_by('emp_no').values('emp_no').distinct()
        context['assetcodes'] = AssetLog.objects.exclude(asset_code=None).order_by('asset_code').values('asset_code').distinct()
        context['assetnames'] = AssetLog.objects.exclude(asset_name=None).order_by('asset_name').values('asset_name').distinct()
        return context

@ajax_login_required
def ajax_assetlog(request):
    if request.method == "POST":
        assetlogs = AssetLog.objects.all()

        return render(request, 'accounts/ajax-assetlog.html', {'assetlogs': assetlogs})

@ajax_login_required
def ajax_assetlog_filter(request):
    if request.method == "POST":
        search_assetno = request.POST.get('search_assetno')
        search_assetname = request.POST.get('search_assetname')
        search_assetcode = request.POST.get('search_assetcode')
        if search_assetno != "" and search_assetcode == "" and search_assetname == "":
            assetlogs = AssetLog.objects.filter(emp_no__iexact=search_assetno)

        elif search_assetno != "" and search_assetcode != "" and search_assetname == "":
            assetlogs = AssetLog.objects.filter(emp_no__iexact=search_assetno, asset_code__iexact=search_assetcode)
        
        elif search_assetno != "" and search_assetcode != "" and search_assetname != "":
            assetlogs = AssetLog.objects.filter(emp_no__iexact=search_assetno, asset_code__iexact=search_assetcode, asset_name__iexact=search_assetname)

        elif search_assetno == "" and search_assetcode != "" and search_assetname == "":
            assetlogs = AssetLog.objects.filter(asset_code__iexact=search_assetcode)

        elif search_assetno == "" and search_assetcode != "" and search_assetname != "":
            assetlogs = AssetLog.objects.filter(asset_code__iexact=search_assetcode, asset_name__iexact=search_assetname)

        elif search_assetno == "" and search_assetcode == "" and search_assetname != "":
            assetlogs = AssetLog.objects.filter(asset_name__iexact=search_assetname)

        elif search_assetno != "" and search_assetcode == "" and search_assetname != "":
            assetlogs = AssetLog.objects.filter(emp_no__iexact=search_assetno,asset_name__iexact=search_assetname)

        return render(request, 'accounts/ajax-assetlog.html', {'assetlogs': assetlogs})

@ajax_login_required
def assetlogadd(request):
    if request.method == "POST":
        emp_no = request.POST.get('emp_no')
        asset_name = request.POST.get('asset_name')
        asset_code = request.POST.get('asset_code')
        check_status = request.POST.get('check_status')
        checkin_date = request.POST.get('checkin_date')
        checkout_date = request.POST.get('checkout_date')
        assetlogid = request.POST.get('assetlogid')
        if assetlogid == "-1":
            try:
                AssetLog.objects.create(
                    emp_no=emp_no,
                    asset_name=asset_name,
                    asset_code=asset_code,
                    check_status=check_status,
                    checkin_date=checkin_date,
                    checkout_date=checkout_date
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Asset Log information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                assetlog = AssetLog.objects.get(id=assetlogid)
                assetlog.emp_no = emp_no
                assetlog.asset_name = asset_name
                assetlog.asset_code = asset_code
                assetlog.check_status = check_status
                assetlog.checkin_date = checkin_date
                assetlog.checkout_date = checkout_date
                assetlog.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Assetlog information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def assetlogdelete(request):
    if request.method == "POST":
        assetlogid = request.POST.get('assetlogid')
        assetlog = AssetLog.objects.get(id=assetlogid)
        assetlog.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getAssetlog(request):
    if request.method == "POST":
        assetlogid = request.POST.get('assetlogid')
        assetlog = AssetLog.objects.get(id=assetlogid)
        data = {
            'emp_no': assetlog.emp_no,
            'asset_name': assetlog.asset_name,
            'asset_code': assetlog.asset_code,
            'check_status': assetlog.check_status,
            'checkin_date': assetlog.checkin_date.strftime('%d %b, %Y %H:%M'),
            'checkout_date': assetlog.checkout_date.strftime('%d %b, %Y %H:%M')

        }
        return JsonResponse(json.dumps(data), safe=False)


#OT calculation part
@method_decorator(login_required, name='dispatch')
class OtcalculationList(ListView):
    model = OTCalculation
    template_name = "accounts/ot_calculation.html"

@method_decorator(login_required, name='dispatch')
class OtcalculationSummary(ListView):
    model = OTCalculation
    template_name = "accounts/ot-calculation-summary.html"

@method_decorator(login_required, name='dispatch')
class OtcalculationFilterSummary(ListView):
    model = OTCalculation
    template_name = "accounts/ot-calculation-filter-summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        checkin_time = self.kwargs.get('checkin_time')
        checkout_time = self.kwargs.get('checkout_time')
        context['checkin_time'] = checkin_time
        context['checkout_time'] = checkout_time

        return context

@ajax_login_required
def ajax_otcalculation(request):
    if request.method == "POST":
        current_year = datetime.datetime.today().year
        current_month = datetime.datetime.today().month
        str_query = "SELECT W.id, O.approved_hour, W.emp_no, W.projectcode, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_ot as O WHERE W.projectcode = O.proj_id and DATE(W.checkin_time) = DATE(O.date) AND YEAR(W.checkin_time) = " + str(current_year) + " AND  MONTH(W.checkin_time) = " + str(current_month) + " ORDER BY W.checkin_time ASC"
        query_ots = WorkLog.objects.raw(str_query)
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                holiday_modetime = datetime.timedelta(hours=8)
                t = q.checkout_time
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
            
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = ph_min_check//15
                    if ph_mins > 32:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25 - 1)
                        q.meal_allowance = 0
                    else:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25)
                        q.meal_allowance = 0
                else:
                    if timediff > modetime:
                        min_check = (timediff - modetime).total_seconds()//60
                        mins = min_check//15
                        if mins >= 20:
                            q.firsthr = str(mins*0.25 - 0.5)
                            q.secondhr = 0
                            q.meal_allowance = 1
                            
                        else:
                            q.firsthr = str(mins*0.25)
                            q.secondhr = 0
                            q.meal_allowance = 0

                    else:
                        q.firsthr = str(0)
                        q.secondhr = 0
                        q.meal_allowance = 0
                
        return render(request, 'accounts/ajax-otcalculation.html', {'otcalculations': query_ots})

@ajax_login_required
def ajax_otcalculation_summary(request):
    if request.method == "POST":
        str_query = "SELECT F.id, F.emp_no,U.basic_salary,F.approved_hour, F.projectcode, F.checkin_time, F.checkout_time FROM (SELECT W.id, O.approved_hour, W.emp_no, W.projectcode, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_ot as O WHERE W.projectcode = O.proj_id and DATE(W.checkin_time) = DATE(O.date)) AS F, tb_user AS U WHERE F.emp_no = U.empid ORDER BY F.checkin_time ASC"
        query_ots = WorkLog.objects.raw(str_query)
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                holiday_modetime = datetime.timedelta(hours=8)
                t = q.checkout_time
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
            
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = ph_min_check//15
                    if ph_mins > 32:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25 - 1)
                        q.meal_allowance = 0
                    else:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25)
                        q.meal_allowance = 0
                else:
                    if timediff > modetime:
                        min_check = (timediff - modetime).total_seconds()//60
                        mins = min_check//15
                        if mins >= 20:
                            q.firsthr = str(mins*0.25 - 0.5)
                            q.secondhr = 0
                            q.meal_allowance = 1
                            
                        else:
                            q.firsthr = str(mins*0.25)
                            q.secondhr = 0
                            q.meal_allowance = 0

                    else:
                        q.firsthr = str(0)
                        q.secondhr = 0
                        q.meal_allowance = 0

        empdata = []
        summary_data = []
        for query_ot in query_ots:
            if str(query_ot.emp_no) in empdata:
                pass 
            else:
                empdata.append(query_ot.emp_no)
        
        for empd in empdata:
            summary_firsthr = 0
            summary_secondhr = 0
            summary_meal = 0
            base_salary = ""
            for query_ot in query_ots:
                if empd == query_ot.emp_no:
                    base_salary = query_ot.basic_salary
                    s_firstht = min(float(query_ot.approved_hour), float(query_ot.firsthr))
                    s_secondht = min(float(query_ot.approved_hour), float(query_ot.secondhr))
                    summary_firsthr += float(s_firstht)
                    summary_secondhr += float(s_secondht)
                    summary_meal += float(query_ot.meal_allowance)
            summary_data.append({
                'emp_no': empd,
                'basic_salary': base_salary,
                'firsthr': summary_firsthr,
                'secondhr': summary_secondhr,
                'meal_allowance': summary_meal,
            })
        
        return render(request, 'accounts/ajax-otcalculation-summary.html', {'otsummaries': summary_data})

@ajax_login_required
def ajax_otcalculation_filter_summary(request):
    if request.method == "POST":
        checkin_time = request.POST.get('checkin_time')
        checkout_time = request.POST.get('checkout_time')
        str_query = "SELECT F.id, F.emp_no,U.basic_salary,F.approved_hour, F.projectcode, F.checkin_time, F.checkout_time FROM (SELECT W.id, O.approved_hour, W.emp_no, W.projectcode, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_ot as O WHERE W.projectcode = O.proj_id and DATE(W.checkin_time) = DATE(O.date)) AS F, tb_user AS U WHERE F.emp_no = U.empid" + " AND F.checkin_time >= " + "'" + checkin_time + "'" + " AND F.checkout_time <= " + "'" + checkout_time + "'"
        query_ots = WorkLog.objects.raw(str_query)
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                holiday_modetime = datetime.timedelta(hours=8)
                t = q.checkout_time
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
            
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = ph_min_check//15
                    if ph_mins > 32:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25 - 1)
                        q.meal_allowance = 0
                    else:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25)
                        q.meal_allowance = 0
                else:
                    if timediff > modetime:
                        min_check = (timediff - modetime).total_seconds()//60
                        mins = min_check//15
                        if mins >= 20:
                            q.firsthr = str(mins*0.25 - 0.5)
                            q.secondhr = 0
                            q.meal_allowance = 1
                            
                        else:
                            q.firsthr = str(mins*0.25)
                            q.secondhr = 0
                            q.meal_allowance = 0

                    else:
                        q.firsthr = str(0)
                        q.secondhr = 0
                        q.meal_allowance = 0

        empdata = []
        summary_filter_data = []
        for query_ot in query_ots:
            if str(query_ot.emp_no) in empdata:
                pass 
            else:
                empdata.append(query_ot.emp_no)
                
        for empd in empdata:
            summary_firsthr = 0
            summary_secondhr = 0
            summary_meal = 0
            base_salary = ""
            for query_ot in query_ots:
                if str(empd) == str(query_ot.emp_no):
                    base_salary = query_ot.basic_salary
                    s_firstht = min(float(query_ot.approved_hour), float(query_ot.firsthr))
                    s_secondht = min(float(query_ot.approved_hour), float(query_ot.secondhr))
                    summary_firsthr += float(s_firstht)
                    summary_secondhr += float(s_secondht)
                    summary_meal += float(query_ot.meal_allowance)
            summary_filter_data.append({
                'emp_no': empd,
                'basic_salary': base_salary,
                'firsthr': summary_firsthr,
                'secondhr': summary_secondhr,
                'meal_allowance': summary_meal,
            })
        
        return render(request, 'accounts/ajax-otcalculation-summary.html', {'otsummaries': summary_filter_data})

@ajax_login_required
def ajax_otcalculation_filter(request):
    if request.method == "POST":
        checkin_time = request.POST.get('checkin_time')
        checkout_time = request.POST.get('checkout_time')
        str_query = "SELECT F.id, F.approved_hour, F.emp_no, F.projectcode, F.checkin_time, F.checkout_time FROM (SELECT W.id, O.approved_hour, W.emp_no, W.projectcode, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_ot as O WHERE W.projectcode = O.proj_id and DATE(W.checkin_time) = DATE(O.date)) AS F WHERE F.checkin_time >= " + "'" + checkin_time + "'" + " AND F.checkout_time <= " + "'" + checkout_time + "'"
        query_ots = WorkLog.objects.raw(str_query)
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                t = q.checkout_time
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
                
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = ph_min_check//15
                    if ph_mins > 32:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25 - 1)
                        q.meal_allowance = 0
                    else:
                        q.firsthr = 0
                        q.secondhr = str(ph_mins*0.25)
                        q.meal_allowance = 0
                else:
                    if timediff > modetime:
                        min_check = (timediff - modetime).total_seconds()//60
                        mins = min_check//15
                        # mins_remain = min_check%15
                        if mins >= 20:
                            q.firsthr = str(mins*0.25 - 0.5)
                            q.secondhr = 0
                            q.meal_allowance = 1
                            
                        else:
                            q.firsthr = str(mins*0.25)
                            q.secondhr = 0
                            q.meal_allowance = 0
                    else:
                        q.firsthr = str(0)
                        q.secondhr = 0
                        q.meal_allowance = 0

        return render(request, 'accounts/ajax-otcalculation.html', {'otcalculations': query_ots})

@ajax_login_required
def otcalculationadd(request):
    if request.method == "POST":
        emp_no = request.POST.get('emp_no')
        project_no = request.POST.get('project_no')
        time_in = request.POST.get('time_in')
        time_out = request.POST.get('time_out')
        approved_ot_hr = request.POST.get('approved_ot_hr')
        firsthr = request.POST.get('firsthr')
        secondhr = request.POST.get('secondhr')
        meal_allowance = request.POST.get('meal_allowance')
        otcalculationid = request.POST.get('otcalculationid')
        if otcalculationid == "-1":
            try:
                OTCalculation.objects.create(
                    emp_no=emp_no,
                    project_no=project_no,
                    time_in=time_in,
                    time_out=time_out,
                    approved_ot_hr=approved_ot_hr,
                    firsthr=firsthr,
                    secondhr=secondhr,
                    meal_allowance=meal_allowance
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "OT Calculation information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                otcalculation = OTCalculation.objects.get(id=otcalculationid)
                otcalculation.emp_no = emp_no
                otcalculation.project_no = project_no
                otcalculation.time_in = time_in
                otcalculation.time_out = time_out
                otcalculation.approved_ot_hr = approved_ot_hr
                otcalculation.firsthr = firsthr
                otcalculation.secondhr = secondhr
                otcalculation.meal_allowance = meal_allowance
                otcalculation.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "OT Calculation information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def otcalculationdelete(request):
    if request.method == "POST":
        otcalculationid = request.POST.get('otcalculationid')
        otcalculation = OTCalculation.objects.get(id=otcalculationid)
        otcalculation.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getOtcalculation(request):
    if request.method == "POST":
        otcalculationid = request.POST.get('otcalculationid')
        otcalculation = OTCalculation.objects.get(id=otcalculationid)
        data = {
            'emp_no': otcalculation.emp_no,
            'project_no': otcalculation.project_no,
            'time_in': otcalculation.time_in.strftime('%d %b, %Y %H:%M'),
            'time_out': otcalculation.time_out.strftime('%d %b, %Y %H:%M'),
            'approved_ot_hr': otcalculation.approved_ot_hr,
            'firsthr': otcalculation.firsthr,
            'secondhr': otcalculation.secondhr,
            'meal_allowance': otcalculation.meal_allowance,


        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def ajax_notification_privilege(request):
    if request.method == "POST": 
        project_no_created = request.POST.get('projectno_created')     
        project_status = request.POST.get('project_status')
        project_end = request.POST.get('project_end')     
        tbm_no_created = request.POST.get('tbm_no_created')
        inventory_item_deleted = request.POST.get('delete_item')     
        stock_equal_restock = request.POST.get('restockqty')
        do_status = request.POST.get('do_status')
        usergroup_created = request.POST.get('usergroup_created')
        service_status = request.POST.get('service_status')
        user_no_created = request.POST.get('user_no')
        pc_status = request.POST.get('pc_status')
        claim_no_created = request.POST.get('claim_no_created')
        contract_end = request.POST.get('contract_end')
        hardware_end = request.POST.get('hardware_end')
        schedule_end = request.POST.get('schedule_end')
        password_change = request.POST.get('password_change')
        username = request.POST.get('username')
        if NotificationPrivilege.objects.filter(user_id=username).exists():
            noprivilege = NotificationPrivilege.objects.get(user_id=username)
            noprivilege.project_no_created = project_no_created
            noprivilege.project_status = project_status
            noprivilege.project_end = project_end
            noprivilege.tbm_no_created = tbm_no_created
            noprivilege.inventory_item_deleted = inventory_item_deleted
            noprivilege.stock_equal_restock = stock_equal_restock
            noprivilege.do_status = do_status
            noprivilege.usergroup_created = usergroup_created
            noprivilege.service_status = service_status
            noprivilege.user_no_created = user_no_created
            noprivilege.pc_status = pc_status
            noprivilege.claim_no_created = claim_no_created
            noprivilege.contract_end = contract_end
            noprivilege.hardware_end = hardware_end
            noprivilege.schedule_end = schedule_end
            noprivilege.password_change = password_change
            noprivilege.save()
        else:
            NotificationPrivilege.objects.create(
                user_id=username,
                project_no_created = project_no_created,
                project_status = project_status,
                project_end = project_end,
                tbm_no_created = tbm_no_created,
                inventory_item_deleted = inventory_item_deleted,
                stock_equal_restock = stock_equal_restock,
                do_status = do_status,
                usergroup_created = usergroup_created,
                service_status = service_status,
                user_no_created = user_no_created,
                pc_status = pc_status,
                claim_no_created = claim_no_created,
                contract_end = contract_end,
                hardware_end = hardware_end,
                schedule_end = schedule_end,
                password_change = password_change
                )

        return JsonResponse({"status": "ok"})

@ajax_login_required
def ajax_privilege_user_check(request):
    if request.method == "POST": 
        userid = request.POST.get('userid')
        if Privilege.objects.filter(user_id=userid).exists():
            privilege = Privilege.objects.get(user_id=userid)
            data = {
                'sales_summary': privilege.sales_summary,
                'sales_report': privilege.sales_report,
                'proj_summary': privilege.proj_summary,
                'proj_ot': privilege.proj_ot,
                'invent_material': privilege.invent_material,
                'prof_summary': privilege.prof_summary

            }
            return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def ajax_notification_privilege_user_check(request):
    if request.method == "POST": 
        userid = request.POST.get('userid')
        if NotificationPrivilege.objects.filter(user_id=userid).exists():
            noprivilege = NotificationPrivilege.objects.get(user_id=userid)
            data = {
                'project_no_created': int(noprivilege.project_no_created),
                'project_status': int(noprivilege.project_status),
                'project_end': int(noprivilege.project_end),
                'tbm_no_created': int(noprivilege.tbm_no_created),
                'inventory_item_deleted': int(noprivilege.inventory_item_deleted),
                'stock_equal_restock': int(noprivilege.stock_equal_restock),
                'do_status': int(noprivilege.do_status),
                'service_status': int(noprivilege.service_status),
                'pc_status': int(noprivilege.pc_status),
                'usergroup_created': int(noprivilege.usergroup_created),
                'user_no_created': int(noprivilege.user_no_created),
                'claim_no_created': int(noprivilege.claim_no_created),
                'contract_end': int(noprivilege.contract_end),
                'hardware_end': int(noprivilege.hardware_end),
                'schedule_end': int(noprivilege.schedule_end),
                'password_change': int(noprivilege.password_change),
            }

            return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def ajax_privilege(request):
    if request.method == "POST": 
        salesummery = request.POST.get('salesummery')     
        salereport = request.POST.get('salereport')
        projsummery = request.POST.get('projsummery')     
        projot = request.POST.get('projot')
        inventmat = request.POST.get('inventmat')     
        profsummary = request.POST.get('profsummary')
        username = request.POST.get('username')
        if Privilege.objects.filter(user_id=username).exists():
            privilege = Privilege.objects.get(user_id=username)
            privilege.sales_summary = str(salesummery)
            privilege.sales_report = str(salereport)
            privilege.proj_summary = str(projsummery)
            privilege.proj_ot = str(projot)
            privilege.invent_material = str(inventmat)
            privilege.prof_summary = str(profsummary)
            privilege.save()
        else:
            Privilege.objects.create(
                user_id=username,
                sales_summary = salesummery,
                sales_report = salereport,
                proj_summary = str(projsummery),
                proj_ot = str(projot),
                invent_material = str(inventmat),
                prof_summary = str(profsummary)
                )

        return JsonResponse({"status": "ok"})

def activateAccount(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None  and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        #login(request, user,backend="django.contrib.auth.backends.ModelBackend")
        return redirect('/')
    else:
        return JsonResponse({"status":'Activation link is invalid!'})

@ajax_login_required
def usercertadd(request):
    if request.method == "POST":
        course = request.POST.get('course')
        course_expiry = request.POST.get('course_expiry')
        course_no = request.POST.get('course_no')
        school = request.POST.get('school')
        selected_user = request.POST.get('selected_user')
        sel_user = User.objects.get(id=int(selected_user))
        certid = request.POST.get('certid')
        if certid == "-1":
            try:
                UserCert.objects.create(
                    course=course,
                    course_expiry=course_expiry,
                    course_no=course_no,
                    school=school,
                    emp_id=sel_user.username
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "User Certification information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                usercert = UserCert.objects.get(id=certid)
                usercert.course=course
                usercert.course_expiry=course_expiry
                usercert.course_no=course_no
                usercert.school=school
                usercert.emp_id=sel_user.username
                usercert.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "User Certification information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def userissuetooladd(request):
    if request.method == "POST":
        tdescription = request.POST.get('description')
        tissued_date = request.POST.get('issued_date')
        tuom = request.POST.get('uom')
        tqty = request.POST.get('qty')
        tissued_by = request.POST.get('issued_by')
        selected_user = request.POST.get('selected_user')
        sel_user = User.objects.get(id=int(selected_user))
        toolid = request.POST.get('toolid')
        if toolid == "-1":
            try:
                UserItemTool.objects.create(
                    description=tdescription,
                    issue_date=tissued_date,
                    uom=tuom,
                    qty=tqty,
                    issued_by=tissued_by,
                    emp_id=sel_user.username
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "User Issued Tool information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                usertool = UserItemTool.objects.get(id=toolid)
                usertool.description=tdescription
                usertool.issue_date=tissued_date
                usertool.uom=tuom
                usertool.qty=tqty
                usertool.issued_by=tissued_by
                usertool.emp_id=sel_user.username
                usertool.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "User Issued Tool information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def userissueppeadd(request):
    if request.method == "POST":
        idescription = request.POST.get('idescription')
        issued_date = request.POST.get('issued_date')
        iuom = request.POST.get('iuom')
        iqty = request.POST.get('iqty')
        issued_by = request.POST.get('issued_by')
        selected_user = request.POST.get('selected_user')
        sel_user = User.objects.get(id=int(selected_user))
        issueid = request.POST.get('issueid')
        if issueid == "-1":
            try:
                UserItemIssued.objects.create(
                    description=idescription,
                    issue_date=issued_date,
                    uom=iuom,
                    qty=iqty,
                    empid=sel_user.empid,
                    issued_by=issued_by
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "User Issued Item information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@method_decorator(login_required, name='dispatch')
class NotificationView(ListView):
    model = Notification.Notification
    template_name = "accounts/notification-information.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notifications'] = self.request.user.notifications.all()
        
        return context

@ajax_login_required
def getUserSignature(request):
    if request.method == "POST":
        userid = request.POST.get('userid')
        usersign = User.objects.get(id=userid)
        if usersign.signature:
            data = {
                'signature': usersign.signature.url
            }
        else:
            data = {
                'signature': ""
            }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def updateUserSignature(request):
    if request.method == "POST":
        userid = request.POST.get('userid')
        try:
            usersignature = User.objects.get(id=userid)
            usersignature.signature=request.FILES.get('signature')
            usersignature.save()

            return JsonResponse({
                "status": "Success",
                "messages": "User Signature updated!"
            })

        except IntegrityError as e: 
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

         