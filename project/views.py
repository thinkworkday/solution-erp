import base64
from django.conf import settings
from django.db.models.aggregates import Sum
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from project.models import DOSignature, DoItem, PCSignature, Pc, PcItem, Project, OT, Do, Bom, BomLog, ProjectFile, SRSignature, Sr, SrItem, Team
from accounts.models import Uom, User
from sales.decorater import ajax_login_required
from django.db import IntegrityError
from django.http import JsonResponse
import json
from django.views.generic.detail import DetailView
from django.views import generic
from django.db.models import Q
import datetime
import pytz
import decimal
import requests
from project.resources import BomResource, DoItemResource, ProjectResource, SrItemResource, TeamResource, ProjectOtResource
from accounts.models import Holiday, WorkLog
import os
from sales.models import Company, Contact, Quotation, Scope
from siteprogress.models import SiteProgress
from siteprogress.resources import SiteProgressResource
from toolbox.models import ToolBoxDescription, ToolBoxItem, ToolBoxObjective
from dateutil import parser as date_parser
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, Image, Spacer, TableStyle, PageBreak, Paragraph
from reportlab.pdfgen import canvas
from reportlab.rl_config import defaultPageSize
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape, portrait
from django.core.files.base import ContentFile
# Create your views here.

@method_decorator(login_required, name='dispatch')
class ProjectSummaryView(ListView):
    model = Project
    template_name = "projects/project-summary-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contacts'] = User.objects.all()
        context['customers'] = Project.objects.all().order_by('company_name').values('company_name').distinct()
        context['proj_incharges'] = Project.objects.exclude(proj_incharge=None).order_by('proj_incharge').values('proj_incharge').distinct()
        context['proj_nos'] = Project.objects.all().order_by('proj_id').values('proj_id').distinct()
        context['date_years'] = list(set([d.start_date.year for d in Project.objects.all()]))

        current_year = datetime.datetime.today().year
        if current_year in list(set([d.start_date.year for d in Project.objects.all()])):
            context['exist_current_year'] = True
        else:
            context['exist_current_year'] = False
        return context

def ajax_export_project(request):
    resource = ProjectResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project-summary.csv"'
    return response

def ajax_export_projectot(request):
    resource = ProjectOtResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project-ot.csv"'
    return response

def ajax_import_project(request):
    
    if request.method == 'POST':
        org_column_names = ['proj_id', 'company_name', 'proj_name', 'start_date', 'end_date', 'proj_incharge', 'proj_status']
        
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
                exist_count = Project.objects.filter(proj_id=row["proj_id"]).count()
                if exist_count == 0:
                    try:
                        project = Project(
                            proj_id=row["proj_id"],
                            company_name=row["company_name"],
                            proj_name=row["proj_name"],
                            start_date=datetime.datetime.strptime(row["start_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc), 
                            end_date=datetime.datetime.strptime(row["end_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc), 
                            proj_incharge=row["proj_incharge"],
                            proj_status=row["proj_status"],
                        )
                        project.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        project = Project.objects.filter(proj_id=row["proj_id"])[0]
                        project.proj_id = row["proj_id"]
                        project.company_name = row["company_name"]
                        project.proj_name=row["proj_name"]
                        project.start_date=datetime.datetime.strptime(row["start_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc)
                        project.end_date=datetime.datetime.strptime(row["end_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc)
                        project.proj_incharge=row["proj_incharge"]
                        project.proj_status=row["proj_status"]
                        
                        project.save()
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

def ajax_import_projectot(request):
    
    if request.method == 'POST':
        org_column_names = ['proj_id', 'date', 'approved_hour', 'approved_by', 'proj_name']
        
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
                exist_count = OT.objects.filter(proj_id=row["proj_id"]).count()
                if exist_count == 0:
                    try:
                        projectot = OT(
                            proj_id=row["proj_id"],
                            approved_hour=row["approved_hour"],
                            proj_name=row["proj_name"],
                            date=datetime.datetime.strptime(row["date"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc), 
                            approved_by=row["approved_by"]
                        )
                        projectot.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        projectot = OT.objects.filter(proj_id=row["proj_id"])[0]
                        projectot.proj_id = row["proj_id"]
                        projectot.approved_hour = row["approved_hour"]
                        projectot.proj_name=row["proj_name"]
                        projectot.start_date=datetime.datetime.strptime(row["date"],'%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
                        projectot.approved_by=row["approved_by"]
                        
                        projectot.save()
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
def ajax_summarys(request):
    if request.method == "POST":
        current_year = datetime.datetime.today().year
        projects = Project.objects.filter(start_date__iso_year=current_year)

        return render(request, 'projects/ajax-project.html', {'projects': projects})

@ajax_login_required
def ajax_summarys_filter(request):
    if request.method == "POST":
        search_projectno = request.POST.get('search_projectno')
        incharge_filter = request.POST.get('incharge_filter')
        search_customer = request.POST.get('search_customer')
        search_year = request.POST.get('search_year')
        if search_year:
            if search_projectno != "" and incharge_filter == "" and search_customer == "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno, start_date__iso_year=search_year)

            elif search_projectno != "" and incharge_filter != "" and search_customer == "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno, proj_incharge__iexact=incharge_filter, start_date__iso_year=search_year)
            
            elif search_projectno != "" and incharge_filter != "" and search_customer != "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno, proj_incharge__iexact=incharge_filter, company_name__iexact=search_customer,start_date__iso_year=search_year)

            elif search_projectno == "" and incharge_filter != "" and search_customer == "":
                projects = Project.objects.filter(proj_incharge__iexact=incharge_filter,start_date__iso_year=search_year)

            elif search_projectno == "" and incharge_filter != "" and search_customer != "":
                projects = Project.objects.filter(proj_incharge__iexact=incharge_filter, company_name__iexact=search_customer,start_date__iso_year=search_year)

            elif search_projectno == "" and incharge_filter == "" and search_customer != "":
                projects = Project.objects.filter(company_name__iexact=search_customer,start_date__iso_year=search_year)

            elif search_projectno != "" and incharge_filter == "" and search_customer != "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno,company_name__iexact=search_customer,start_date__iso_year=search_year)

            elif search_projectno == "" and incharge_filter == "" and search_customer == "":
                projects = Project.objects.filter(start_date__iso_year=search_year)
        else:
            if search_projectno != "" and incharge_filter == "" and search_customer == "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno)

            elif search_projectno != "" and incharge_filter != "" and search_customer == "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno, proj_incharge__iexact=incharge_filter)
            
            elif search_projectno != "" and incharge_filter != "" and search_customer != "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno, proj_incharge__iexact=incharge_filter, company_name__iexact=search_customer)

            elif search_projectno == "" and incharge_filter != "" and search_customer == "":
                projects = Project.objects.filter(proj_incharge__iexact=incharge_filter)

            elif search_projectno == "" and incharge_filter != "" and search_customer != "":
                projects = Project.objects.filter(proj_incharge__iexact=incharge_filter, company_name__iexact=search_customer)

            elif search_projectno == "" and incharge_filter == "" and search_customer != "":
                projects = Project.objects.filter(company_name__iexact=search_customer)

            elif search_projectno != "" and incharge_filter == "" and search_customer != "":
                projects = Project.objects.filter(proj_id__iexact=search_projectno,company_name__iexact=search_customer)
        return render(request, 'projects/ajax-project.html', {'projects': projects})

@ajax_login_required
def summaryadd(request):
    if request.method == "POST":
        proj_no = request.POST.get('proj_no')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        customer = request.POST.get('customer')
        project = request.POST.get('project')
        
        summaryid = request.POST.get('summaryid')
        if summaryid == "-1":
            try:
                Project.objects.create(
                    proj_id=proj_no,
                    start_date=start_date,
                    end_date=end_date,
                    company_name=customer,
                    proj_name=project
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Summary information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Project is existed!"
                })
        else:
            try:
                summary = Project.objects.get(id=summaryid)
                summary.proj_id = proj_no
                summary.start_date = start_date
                summary.end_date = end_date
                summary.company_name = customer
                summary.proj_name=project
                summary.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Summary information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Project is existed!"
                })

@method_decorator(login_required, name='dispatch')
class ProjectOTView(ListView):
    model = OT
    template_name = "projects/projectOT-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projectots'] = OT.objects.all()
        context['approved_users'] = User.objects.filter(Q(role__icontains='Managers') | Q(role__icontains='Engineers') | Q(is_staff=True))
        context['approveds'] = self.request.user.username

        context['projectot_nos'] = OT.objects.exclude(proj_id=None).order_by('proj_id').values('proj_id').distinct()
        context['proj_nos'] = Project.objects.filter(proj_status="On-going").order_by('proj_id').values('proj_id').distinct()
        return context

@method_decorator(login_required, name='dispatch')
class approvedOTView(ListView):
    model = OT
    template_name = "projects/approved-ot.html"

@ajax_login_required
def ajax_get_projectname(request):
    if request.method == "POST":
        proj_id = request.POST.get('proj_id')
        if Project.objects.filter(proj_id__iexact=proj_id).exists():
            project = Project.objects.get(proj_id__iexact=proj_id)
            data = {
                "status": "exist",
                "project_name": project.proj_name
            }

            return JsonResponse(data)
        else:
            data = {
                "status": "not exist",
            }
            return JsonResponse(data)
# @ajax_login_required
# def check_ot_number(request):
#     if request.method == "POST":
#         if OT.objects.all().exists():
#             ot= OT.objects.all().order_by('-ot_id')[0]
#             data = {
#                 "status": "exist",
#                 "ot_id": ot.ot_id
#             }
        
#             return JsonResponse(data)
#         else:
#             data = {
#                 "status": "no exist"
#             }
        
#             return JsonResponse(data)

@ajax_login_required
def ajax_projectots(request):
    if request.method == "POST":
        current_year = datetime.datetime.today().year
        current_month = datetime.datetime.today().month
        projectots = OT.objects.filter(date__year=current_year, date__month=current_month)

        return render(request, 'projects/ajax-projectot.html', {'projectots': projectots})

@ajax_login_required
def ajax_projectots_filter(request):
    if request.method == "POST":
        search_projectno = request.POST.get('search_projectno')
        daterange = request.POST.get('daterange')
        if daterange:
            startdate = datetime.datetime.strptime(daterange.split()[0],'%Y.%m.%d').replace(tzinfo=pytz.utc)
            enddate = datetime.datetime.strptime(daterange.split()[2], '%Y.%m.%d').replace(tzinfo=pytz.utc)
        search_approved = request.POST.get('search_approved')
        if search_projectno != "" and daterange == "" and search_approved == "":
            projectots = OT.objects.filter(proj_id__iexact=search_projectno)

        elif search_projectno != "" and daterange != "" and search_approved == "":
            projectots = OT.objects.filter(proj_id__iexact=search_projectno, date__gte=startdate, date__lte=enddate)
        
        elif search_projectno != "" and daterange != "" and search_approved != "":
            projectots = OT.objects.filter(proj_id__iexact=search_projectno, date__gte=startdate, date__lte=enddate, approved_by__iexact=search_approved)

        elif search_projectno == "" and daterange != "" and search_approved == "":
            projectots = OT.objects.filter(date__gte=startdate, date__lte=enddate)

        elif search_projectno == "" and daterange != "" and search_approved != "":
            projectots = OT.objects.filter(date__gte=startdate, date__lte=enddate, approved_by__iexact=search_approved)

        elif search_projectno == "" and daterange == "" and search_approved != "":
            projectots = OT.objects.filter(approved_by__iexact=search_approved)

        elif search_projectno != "" and daterange == "" and search_approved != "":
            projectots = OT.objects.filter(proj_id__iexact=search_projectno,approved_by__iexact=search_approved)

        return render(request, 'projects/ajax-projectot.html', {'projectots': projectots})


@ajax_login_required
def getProjectSummary(request):
    if request.method == "POST":
        summaryid = request.POST.get('summaryid')
        summary = Project.objects.get(id=summaryid)
        if summary.end_date:
            data = {
                'proj_id': summary.proj_id,
                'start_date': summary.start_date.strftime('%d %b, %Y'),
                'end_date': summary.end_date.strftime('%d %b, %Y'),
                'customer': str(summary.company_name),
                'proj_name': summary.proj_name
            }
        else:
            data = {
            'proj_id': summary.proj_id,
            'start_date': summary.start_date.strftime('%d %b, %Y'),
            'end_date': "",
            'customer': str(summary.company_name),
            'proj_name': summary.proj_name
        }
        return JsonResponse(json.dumps(data), safe=False)

@method_decorator(login_required, name='dispatch')
class ProjectDetailView(DetailView):
    model = Project
    template_name="projects/project-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        summary = Project.objects.get(id=content_pk)
        context['companies'] = Company.objects.all()
        context['summary'] = summary
        context['project_pk'] = content_pk
        context['contacts'] = Contact.objects.all()
        context['contact_users'] = User.objects.all()
        context['uoms'] = Uom.objects.all()
        context['projects_incharge'] = User.objects.filter(Q(role__icontains='Managers') | Q(role__icontains='Engineers') | Q(is_staff=True))
        context['dolist'] = Do.objects.filter(project_id=content_pk)
        context['filelist'] = ProjectFile.objects.filter(project_id=content_pk)
        context['bomlist'] = Bom.objects.filter(project_id=content_pk)
        context['teamlist'] = Team.objects.filter(project_id=content_pk)
        context['srlist'] = Sr.objects.filter(project_id=content_pk)
        context['pclist'] = Pc.objects.filter(project_id=content_pk)
        quotation = summary.quotation
        projectitems = Scope.objects.filter(quotation_id=quotation.id,parent=None)       
        for obj in projectitems:
            obj.childs = Scope.objects.filter(quotation_id=quotation.id, parent_id=obj.id)
            obj.cumulativeqty = SiteProgress.objects.filter(project_id=content_pk,description__iexact=obj.description).aggregate(Sum('qty'))['qty__sum']
            if obj.allocation_perc and obj.cumulativeqty:
                obj.cumulativeperc = float(obj.cumulativeqty / obj.qty) * float(obj.allocation_perc)
            else:
                obj.cumulativeperc = 0
            for subobj in obj.childs:
                
                subobj.cumulativeqty = SiteProgress.objects.filter(project_id=content_pk,description__iexact=subobj.description).aggregate(Sum('qty'))['qty__sum']
                if subobj.allocation_perc and subobj.cumulativeqty:
                    subobj.cumulativeperc = float(subobj.cumulativeqty / subobj.qty) * float(subobj.allocation_perc)
                else:
                    subobj.cumulativeperc = 0

        subtotal = 0
        for allobj in Scope.objects.filter(quotation_id=quotation.id):
            allobj.cumulativeqty = SiteProgress.objects.filter(project_id=content_pk,description__iexact=allobj.description).aggregate(Sum('qty'))['qty__sum']
            if allobj.allocation_perc and allobj.cumulativeqty:
                allobj.cumulativeperc = float(allobj.cumulativeqty / allobj.qty) * float(allobj.allocation_perc)
            else:
                allobj.cumulativeperc = 0
            subtotal = subtotal + allobj.cumulativeperc

        context['projectitems'] = projectitems
        context['projectitemall'] = Scope.objects.filter(quotation_id=quotation.id)
        context['quotation_pk'] = quotation.id
        context['subtotal'] = subtotal
        site_progress = SiteProgress.objects.filter(project_id=content_pk)
        context['site_progress'] = site_progress
        projectitemactivitys = Scope.objects.filter(quotation_id=quotation.id)
        context['projectitemactivitys'] = projectitemactivitys
        context['toolboxitems'] = ToolBoxItem.objects.filter(project_id=content_pk, manager="Engineer")
        context['tbm_objectives'] = ToolBoxObjective.objects.all()
        context['tbm_descriptions'] = ToolBoxDescription.objects.all()
        return context

@ajax_login_required
def ajax_filter_description(request):
    if request.method == "POST":
        toolbox_objective = request.POST.get('toolbox_objective')
        descriptions = ToolBoxDescription.objects.filter(objective_id = toolbox_objective)
        return render(request, 'projects/ajax-tbm-description.html', {'descriptions': descriptions})

@ajax_login_required
def ajax_add_proj_file(request):
    if request.method == "POST":
        name = request.POST.get('filename')
        fileid = request.POST.get('fileid')
        projectid = request.POST.get('projectid')
        if fileid == "-1":
            try:
                ProjectFile.objects.create(
                    name=name,
                    document = request.FILES.get('document'),
                    uploaded_by_id=request.user.id,
                    project_id = projectid,
                    date=datetime.datetime.now().date()
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Project File information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def ajax_all_mandays(request):
    if request.method == "POST":
        proj_id = request.POST.get('proj_id')
        str_query = "SELECT F.id, F.projectcode,  F.emp_no, F.estimated_mandays, F.start_date, F.end_date, F.projectcode, F.checkin_time, F.checkout_time FROM (SELECT W.id, W.projectcode, W.emp_no, P.estimated_mandays, P.start_date, P.end_date, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_project as P WHERE W.projectcode = P.proj_id) AS F WHERE F.projectcode = " + "'" + proj_id + "'" + " ORDER BY Date(F.checkin_time), F.emp_no"
        query_ots = WorkLog.objects.raw(str_query)
        total_1hr = 0
        total_2hr = 0

        if len(query_ots) > 0:
            estimated_mandays = query_ots[0].estimated_mandays
            actual_mondays = 1
            temp_emp_no = query_ots[0].emp_no
            temp_checkin = query_ots[0].checkin_time.date()
        else:
            estimated_mandays = ""
            actual_mondays = 0
            temp_emp_no = ""
            temp_checkin = ""
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                holiday_modetime = datetime.timedelta(hours=8)
                t = q.checkout_time
                #q.estimate_day = (q.checkout_time.date() - q.checkin_time.date()).days
                q.estimate_day = (q.end_date - q.start_date).days
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = int(ph_min_check//15)
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
                if temp_emp_no == q.emp_no and temp_checkin == q.checkin_time.date():
                    pass
                else:
                    actual_mondays += 1
                    temp_emp_no = q.emp_no
                    temp_checkin = q.checkin_time.date()
        if len(query_ots) > 0:
            temp_emp_no1 = query_ots[0].emp_no
            temp_checkin1 = query_ots[0].checkin_time.date()
            total_1hr = float(query_ots[0].firsthr)
            total_2hr = float(query_ots[0].secondhr)
            for q in query_ots:
                if q.checkout_time is not None and q.checkin_time is not None:
                    if temp_emp_no1 == q.emp_no and temp_checkin1 == q.checkin_time.date():
                        pass
                    else:
                        total_1hr += float(q.firsthr)
                        total_2hr += float(q.secondhr)
                        temp_emp_no1 = q.emp_no
                        temp_checkin1 = q.checkin_time.date()
        return render(request, 'projects/ajax-mandays-list.html', {'mandays': query_ots,'estimated_mandays': estimated_mandays, 'actual_mondays': actual_mondays, 'total_1hr': total_1hr, 'total_2hr': total_2hr})

@ajax_login_required
def ajax_filter_mandays(request):
    if request.method == "POST":
        proj_id = request.POST.get('proj_id')
        startDate = request.POST.get('startDate')
        endDate = request.POST.get('endDate')
        str_query = "SELECT F.id, F.approved_hour, F.emp_no, F.projectcode, F.checkin_time, F.checkout_time FROM (SELECT W.id, W.emp_no, O.approved_hour, W.projectcode, W.checkin_time, W.checkout_time FROM tb_worklog AS W, tb_ot as O WHERE W.projectcode = O.proj_id and DATE(W.checkin_time) = DATE(O.date)) AS F WHERE F.projectcode = " + "'" + proj_id + "'" + "AND F.checkin_time >= " + "'" + startDate + "'" + " AND F.checkout_time <= " + "'" + endDate + "'"
        query_ots = WorkLog.objects.raw(str_query)
        total_1hr = 0
        total_2hr = 0
        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                modetime = datetime.timedelta(hours=17)
                t = q.checkout_time
                q.estimate_day = (q.checkout_time.date() - q.checkin_time.date()).days
                if q.checkout_time.date() > q.checkin_time.date():
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second) + datetime.timedelta(hours=24)
                else:
                    timediff = datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                check_weekday = q.checkin_time.weekday()
                check_holiday = Holiday.objects.filter(date=q.checkin_time.date()).exists()
                if check_weekday == 6 or check_holiday == True:
                    ph_min_check = (q.checkout_time - q.checkin_time).total_seconds()//60
                    ph_mins = int(ph_min_check//15)
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

        for q in query_ots:
            if q.checkout_time is not None and q.checkin_time is not None:
                total_1hr += float(str(q.firsthr).replace('HR', ''))
                total_2hr += float(str(q.secondhr).replace('HR', ''))
        return render(request, 'projects/ajax-mandays-list.html', {'mandays': query_ots, 'total_1hr': total_1hr, 'total_2hr': total_2hr})

@ajax_login_required
def UpdateSummary(request):
    if request.method == "POST":
        
        company_name = request.POST.get('company_name')
        proj_name = request.POST.get('proj_name')
        worksite_address = request.POST.get('worksite_address')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        proj_incharge = request.POST.get('proj_incharge')
        site_incharge = request.POST.get('site_incharge')
        proj_postalcode = request.POST.get('postal_code')
        site_tel = request.POST.get('site_tel')
        RE = request.POST.get('re')
        proj_id = request.POST.get('proj_id')
        qtt_id = request.POST.get('qtt_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        # latitude = request.POST.get('latitude')
        # longitude = request.POST.get('longitude')
        proj_status = request.POST.get('proj_status')
        variation_order = request.POST.get('variation_order')
        note = request.POST.get('note')
        summaryid = request.POST.get('summaryid')

        payload = {
            'searchVal': proj_postalcode, 
            'returnGeom': 'Y',
            'getAddrDetails': 'Y',
            'pageNum': '1'
        }
        #get long and lat data using postal code
        mapinfo = requests.get('https://developers.onemap.sg/commonapi/search',headers={"content-type":"application/json"}, params=payload)
        lat_lon_data = mapinfo.json()["results"]
        if(len(lat_lon_data) != 0):
            latitude = lat_lon_data[0]["LATITUDE"]
            longitude = lat_lon_data[0]["LONGITUDE"]
        else:
            latitude = ""
            longitude = ""
        try:
            summary = Project.objects.get(id=summaryid)
            
            summary.company_name_id=company_name
            summary.proj_name=proj_name
            summary.worksite_address=worksite_address
            summary.contact_person_id=contact_person
            summary.email=email
            summary.tel=tel
            summary.fax=fax
            summary.qtt_id=qtt_id
            summary.proj_id=proj_id
            summary.proj_incharge=proj_incharge
            summary.site_incharge=site_incharge
            summary.site_tel=site_tel
            summary.start_date=start_date
            summary.end_date=end_date
            summary.proj_postalcode = proj_postalcode
            summary.latitude=latitude
            summary.longitude=longitude
            summary.proj_status=proj_status
            summary.variation_order=variation_order
            summary.note=note
            summary.RE=RE
            summary.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Project Summary information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@ajax_login_required
def summarydelete(request):
    if request.method == "POST":
        summaryid = request.POST.get('summaryid')
        summary = Project.objects.get(id=summaryid)
        summary.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def otadd(request):
    if request.method == "POST":
        proj_id = request.POST.get('proj_id')
        date = request.POST.get('date')
        approved_hour = request.POST.get('approved_hour')
        approved_by = request.POST.get('approved_by')
        comment = request.POST.get('comment')
        proj_name = request.POST.get('proj_name')
        
        otid = request.POST.get('otid')
        if otid == "-1":
            try:
                if OT.objects.filter(proj_id__iexact=proj_id, date__date=date.split(" ")[0]).exists():
                    return JsonResponse({
                        "status": "Error",
                        "messages": "Already Data is existed!"
                    })
                else:

                    OT.objects.create(
                        proj_id=proj_id,
                        date=date_parser.parse(date).replace(tzinfo=pytz.utc),
                        approved_hour=approved_hour,
                        approved_by=approved_by,
                        comment=comment,
                        proj_name=proj_name
                    )
                    return JsonResponse({
                        "status": "Success",
                        "messages": "OT information added!"
                    })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                ot = OT.objects.get(id=otid)
                ot.proj_id = proj_id
                ot.date = date
                ot.approved_hour = approved_hour
                ot.approved_by = approved_by
                ot.comment = comment
                ot.proj_name=proj_name
                ot.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "OT information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })


@ajax_login_required
def getProjectOt(request):
    if request.method == "POST":
        otid = request.POST.get('otid')
        ot = OT.objects.get(id=otid)
        data = {
            'proj_id': ot.proj_id,
            'date': ot.date.strftime('%d %b, %Y %H:%M'),
            'comment': ot.comment,
            'approved_by': ot.approved_by,
            'proj_name': ot.proj_name,
            'approved_hour': ot.approved_hour
        }
        return JsonResponse(json.dumps(data, cls=DecimalEncoder), safe=False)


@ajax_login_required
def otdelete(request):
    if request.method == "POST":
        otid = request.POST.get('otid')
        ot = OT.objects.get(id=otid)
        ot.delete()

        return JsonResponse({'status': 'ok'})

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

@ajax_login_required
def check_do_number(request):
    if request.method == "POST":
        if Do.objects.all().exists():
            do= Do.objects.all().order_by('-do_no')[0]
            data = {
                "status": "exist",
                "do_no": do.do_no.replace('CDO','').split()[0]
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def getBom(request):
    if request.method == "POST":
        bomid = request.POST.get('bomid')
        bom = Bom.objects.get(id=bomid)
        if bom.date:

            data = {
                'description': bom.description,
                'uom': bom.uom_id,
                'ordered_qty': bom.ordered_qty,
                'brand': bom.brand,
                'delivered_po_no': bom.delivered_po_no,
                'date': bom.date.strftime('%d %b, %Y'),
                'remark': bom.remark,
            }
        else:
            data = {
                'description': bom.description,
                'uom': bom.uom_id,
                'ordered_qty': bom.ordered_qty,
                'brand': bom.brand,
                'delivered_po_no': bom.delivered_po_no,
                'date': '',
                'remark': bom.remark,
            }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def bomadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        uom = request.POST.get('uom')
        ordered_qty = request.POST.get('ordered_qty')
        brand = request.POST.get('brand')
        delivery_qty = request.POST.get('delivery_qty')
        if(delivery_qty == ""):
            delivery_qty = 0
        delivered_po_no = request.POST.get('delivered_po_no')
        date = request.POST.get('date')
        if date == "":
            date = None
        remark = request.POST.get('remark')
        projectid = request.POST.get('projectid')
        bomid = request.POST.get('bomid')
        if bomid == "-1":
            try:
                Bom.objects.create(
                    description=description,
                    uom_id=uom,
                    ordered_qty=ordered_qty,
                    brand=brand,
                    delivered_qty=delivery_qty,
                    delivered_po_no=delivered_po_no,
                    date=date,
                    remark=remark,
                    project_id=projectid,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Bom information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Bom is existed!"
                })
        else:
            try:
                bom = Bom.objects.get(id=bomid)
                bom.description = description
                bom.uom_id = uom
                bom.ordered_qty = ordered_qty
                bom.brand = brand
                bom.delivered_qty=delivery_qty
                bom.delivered_po_no=delivered_po_no
                bom.date = date
                bom.remark=remark
                bom.project_id = projectid
                bom.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Bom information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Bom is existed!"
                })

@ajax_login_required
def bomlogadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        uom = request.POST.get('uom')
        delivered_qty = request.POST.get('delivered_qty')
        if(delivered_qty == ""):
            delivered_qty = 0
        do_no = request.POST.get('do_no')
        date = request.POST.get('date')
        if date == "":
            date = None
        remark = request.POST.get('remark')
        projectid = request.POST.get('projectid')
        bomid = request.POST.get('bomid')
        bomlogid = request.POST.get('bomlogid')
        if bomlogid == "-1":
            try:
                BomLog.objects.create(
                    description=description,
                    uom_id=uom,
                    delivered_qty=delivered_qty,
                    do_no=do_no,
                    date=date,
                    remark=remark,
                    bom_id=bomid,
                    project_id=projectid,
                )
                total_delivered_qty = BomLog.objects.filter(bom_id=bomid, project_id=projectid).aggregate(Sum('delivered_qty'))['delivered_qty__sum']
                bom = Bom.objects.get(id=bomid)
                bom.delivered_qty = total_delivered_qty
                bom.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "Bom Log information added!"
                })
            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Bom Log is existed!"
                })

@ajax_login_required
def doadd(request):
    if request.method == "POST":
        do_no = request.POST.get('do_no')
        date = request.POST.get('dodate')
        if date == "":
            date = None
        projectid = request.POST.get('projectid')
        doid = request.POST.get('doid')
        # if request.user.signature != "":
        #     status = "Signed"
        # else:
        #     status = "Open"
        if doid == "-1":
            try:
                do = Do.objects.create(
                    do_no=do_no,
                    date=date,
                    status="Open",
                    created_by_id=request.user.id,
                    project_id=projectid,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Do information added!",
                    "newDoId": do.id,
                    "method": "add"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Do is existed!",
                })
        else:
            try:
                do = Do.objects.get(id=doid)
                do.do_no = do_no
                do.date = date
                do.created_by_id=request.user.id
                # do.status = "Open"
                do.upload_by_id=request.user.id
                # do.project_id = projectid
                do.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Do information updated!",
                    "newDoId": do.id,
                    "method": "update"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Do is existed!"
                })

@ajax_login_required
def dodocadd(request):
    if request.method == "POST":
        projectid = request.POST.get('projectid')
        dodocid = request.POST.get('dodocid')
        try:
            do = Do.objects.get(id=dodocid)
            do.upload_by_id=request.user.id
            do.project_id = projectid
            if request.FILES.get('document'):
                do.document = request.FILES.get('document')
                do.status = "Signed"
            do.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Do Document uploaded!"
            })

        except IntegrityError as e: 
            return JsonResponse({
                "status": "Error",
                "messages": "Error!"
            })

@ajax_login_required
def srdocadd(request):
    if request.method == "POST":
        projectid = request.POST.get('projectid')
        srdocid = request.POST.get('srdocid')
        try:
            sr = Sr.objects.get(id=srdocid)
            sr.uploaded_by_id=request.user.id
            sr.project_id = projectid
            if request.FILES.get('document'):
                sr.document = request.FILES.get('document')
                sr.status = "Signed"
            sr.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Sr Document uploaded!"
            })

        except IntegrityError as e: 
            return JsonResponse({
                "status": "Error",
                "messages": "Error!"
            })

@ajax_login_required
def pcdocadd(request):
    if request.method == "POST":
        projectid = request.POST.get('projectid')
        pcdocid = request.POST.get('pcdocid')
        try:
            pc = Pc.objects.get(id=pcdocid)
            pc.uploaded_by_id=request.user.id
            pc.project_id = projectid
            if request.FILES.get('document'):
                pc.document = request.FILES.get('document')
                pc.status = "Signed"
            pc.save()

            return JsonResponse({
                "status": "Success",
                "messages": "PC Document uploaded!"
            })

        except IntegrityError as e: 
            return JsonResponse({
                "status": "Error",
                "messages": "Error!"
            })


@ajax_login_required
def teamadd(request):
    if request.method == "POST":
        teamuser = request.POST.get('teamuser')
        priority = request.POST.get('priority')
        teamid = request.POST.get('teamid')
        projectid = request.POST.get('projectid')
        tuser = User.objects.get(id=int(teamuser))
        if teamid == "-1":
            try:
                Team.objects.create(
                    emp_no=tuser.empid,
                    first_name=tuser.first_name,
                    last_name=tuser.last_name,
                    role=tuser.role,
                    priority=priority,
                    project_id=projectid,
                    user_id=tuser.id
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Team information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Team is existed!"
                })
        else:
            try:
                team = Team.objects.get(id=teamid)
                team.emp_no = tuser.empid
                team.first_name = tuser.first_name
                team.last_name = tuser.last_name
                team.role = tuser.role
                team.priority=priority
                team.project_id = projectid
                team.user_id = tuser.id
                team.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Team information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Team is existed!"
                })

@ajax_login_required
def getTeam(request):
    if request.method == "POST":
        teamid = request.POST.get('teamid')
        team = Team.objects.get(id=teamid)
        data = {
            'teamuser': str(team.user_id),
            'priority': team.priority,

        }
        return JsonResponse(json.dumps(data), safe=False)
@ajax_login_required
def deleteTeam(request):
    if request.method == "POST":
        team_id = request.POST.get('team_id')
        team = Team.objects.get(id=team_id)
        team.delete()

        return JsonResponse({'status': 'ok'})
@ajax_login_required
def deleteFile(request):
    if request.method == "POST":
        filedel_id = request.POST.get('filedel_id')
        projfile = ProjectFile.objects.get(id=filedel_id)
        projfile.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deleteBom(request):
    if request.method == "POST":
        bomdel_id = request.POST.get('bomdel_id')
        bom = Bom.objects.get(id=bomdel_id)
        bom.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deleteDo(request):
    if request.method == "POST":
        dodel_id = request.POST.get('dodel_id')
        dodata = Do.objects.get(id=dodel_id)
        dodata.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deleteSR(request):
    if request.method == "POST":
        srdel_id = request.POST.get('srdel_id')
        srdata = Sr.objects.get(id=srdel_id)
        srdata.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deletePc(request):
    if request.method == "POST":
        pcdel_id = request.POST.get('pcdel_id')
        pcdata = Pc.objects.get(id=pcdel_id)
        pcdata.delete()

        return JsonResponse({'status': 'ok'})

def ajax_export_team(request, projectid):
    resource = TeamResource()
    queryset = Team.objects.filter(project_id=projectid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project_team.csv"'
    return response

def ajax_export_bom(request, projectid):
    resource = BomResource()
    queryset = Bom.objects.filter(project_id=projectid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project_bom.csv"'
    return response

def ajax_export_siteprogress(request, projectid):
    resource = SiteProgressResource()
    queryset = SiteProgress.objects.filter(project_id=projectid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="site_progress_log.csv"'
    return response

@method_decorator(login_required, name='dispatch')
class DoDetailView(DetailView):
    model = Do
    pk_url_kwarg = 'dopk'
    template_name="projects/delivery-order-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proj_pk = self.kwargs.get('pk')
        do_pk = self.kwargs.get('dopk')
        summary = Project.objects.get(id=proj_pk)
        context['summary'] = summary
        context['project_pk'] = proj_pk
        context['delivery_pk'] = do_pk
        delivery_order = Do.objects.get(id=do_pk)
        context['contacts'] = User.objects.all()
        context['uoms'] = Uom.objects.all()
        context['companies'] = Company.objects.all()
        context['delivery_order'] = delivery_order
        quotation = Quotation.objects.get(qtt_id__iexact=summary.proj_id.replace('CPJ','').strip())
        context['doitems'] = DoItem.objects.filter(project_id=proj_pk, do_id=do_pk)
        context['quotation'] = quotation
        if(DOSignature.objects.filter(project_id=proj_pk, do_id=do_pk).exists()):
            context['dosignature'] = DOSignature.objects.get(project_id=proj_pk, do_id=do_pk)
        else:
            context['dosignature'] = None
        context['projectitemall'] = Scope.objects.filter(quotation_id=quotation.id)
        return context

@method_decorator(login_required, name='dispatch')
class DoSignatureCreate(generic.CreateView):
    model = DOSignature
    fields = '__all__'
    template_name="projects/delivery-signature.html"

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            DOSignature.objects.create(
                signature=request.POST.get('signature'),
                name=sign_name,
                nric = sign_nric,
                update_date = datetime.datetime.strptime(sign_date,'%d %b %Y'),
                do_id=self.kwargs.get('dopk'),
                project_id=self.kwargs.get('pk')
            )
            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/delivery-order-detail/' + self.kwargs.get('dopk'))

@method_decorator(login_required, name='dispatch')
class DoSignatureUpdate(generic.UpdateView):
    model = DOSignature
    pk_url_kwarg = 'signpk'
    fields = '__all__'
    template_name="projects/delivery-signature.html"
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            doSignature = DOSignature.objects.get(id=self.kwargs.get('signpk'))
            doSignature.signature = request.POST.get('signature')
            doSignature.name = sign_name
            doSignature.nric = sign_nric
            doSignature.update_date = datetime.datetime.strptime(sign_date.replace(',', ""),'%d %b %Y').date()
            doSignature.do_id = self.kwargs.get('dopk')
            doSignature.project_id = self.kwargs.get('pk')
            doSignature.save()

            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/delivery-order-detail/' + self.kwargs.get('dopk'))

@ajax_login_required
def deliverysignadd(request):
    if request.method == "POST":
        name = request.POST.get('name')
        nric = request.POST.get('nric')
        date = request.POST.get('date')
        signature = request.POST.get('signature')
        deliveryid = request.POST.get('deliveryid')
        projectid = request.POST.get('projectid')
        default_base64 = request.POST.get("default_base64")
        doid = request.POST.get('doid')
        
        format, imgstr = default_base64.split(';base64,')
        ext = format.split('/')[-1]
        signature_image = ContentFile(base64.b64decode(imgstr), name='delivery-sign-' + datetime.date.today().strftime("%d-%m-%Y") + "." + ext)
        if deliveryid == "-1":
            try:
                DOSignature.objects.create(
                    name=name,
                    nric=nric,
                    update_date=date,
                    signature=signature,
                    do_id=doid,
                    project_id=projectid,
                    signature_image=signature_image
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Delivery Signature information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                dosignature = DOSignature.objects.get(id=deliveryid)
                dosignature.name=name
                dosignature.nric=nric
                dosignature.update_date=date
                dosignature.signature=signature
                dosignature.do_id=doid
                dosignature.project_id=projectid
                dosignature.signature_image=signature_image
                dosignature.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Delivery Signature information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def getDeliverySign(request):
    if request.method == "POST":
        deliveryid = request.POST.get('deliveryid')
        dosignature = DOSignature.objects.get(id=deliveryid)
        data = {
            'name': dosignature.name,
            'nric': dosignature.nric,
            'date': dosignature.update_date.strftime('%d %b, %Y'),
            'signature': dosignature.signature
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def getServiceSign(request):
    if request.method == "POST":
        serviceid = request.POST.get('serviceid')
        srsignature = SRSignature.objects.get(id=serviceid)
        data = {
            'name': srsignature.name,
            'nric': srsignature.nric,
            'date': srsignature.update_date.strftime('%d %b, %Y'),
            'signature': srsignature.signature
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def servicesignadd(request):
    if request.method == "POST":
        name = request.POST.get('name')
        nric = request.POST.get('nric')
        date = request.POST.get('date')
        signature = request.POST.get('signature')
        serviceid = request.POST.get('serviceid')
        projectid = request.POST.get('projectid')
        default_base64 = request.POST.get("default_base64")
        srid = request.POST.get('srid')
        
        format, imgstr = default_base64.split(';base64,')
        ext = format.split('/')[-1]
        signature_image = ContentFile(base64.b64decode(imgstr), name='service-sign-' + datetime.date.today().strftime("%d-%m-%Y") + "." + ext)
        if serviceid == "-1":
            try:
                SRSignature.objects.create(
                    name=name,
                    nric=nric,
                    update_date=date,
                    signature=signature,
                    sr_id=srid,
                    project_id=projectid,
                    signature_image=signature_image
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Signature information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                srsignature = SRSignature.objects.get(id=serviceid)
                srsignature.name=name
                srsignature.nric=nric
                srsignature.update_date=date
                srsignature.signature=signature
                srsignature.sr_id=srid
                srsignature.project_id=projectid
                srsignature.signature_image=signature_image
                srsignature.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Signature information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def check_sr_number(request):
    if request.method == "POST":
        if Sr.objects.all().exists():
            sr= Sr.objects.all().order_by('-sr_no')[0]
            data = {
                "status": "exist",
                "sr_no": sr.sr_no.replace('CSR','').split()[0]
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def check_pc_number(request):
    if request.method == "POST":
        if Pc.objects.all().exists():
            pc= Pc.objects.all().order_by('-pc_no')[0]
            data = {
                "status": "exist",
                "pc_no": pc.pc_no.replace('CPC','').split()[0]
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def sradd(request):
    if request.method == "POST":
        sr_no = request.POST.get('sr_no')
        date = request.POST.get('srdate')
        if date == "":
            date = None
        projectid = request.POST.get('projectid')
        srid = request.POST.get('srid')
        # if request.user.signature != "":
        #     status = "Signed"
        # else:
        #     status = "Open"
        if srid == "-1":
            try:
                sr = Sr.objects.create(
                    sr_no=sr_no,
                    date=date,
                    status="Open",
                    created_by_id=request.user.id,
                    # uploaded_by_id=request.user.id,
                    project_id=projectid,
                )
                return JsonResponse({
                    "status": "Success",
                    "method": "add",
                    "newSrID": sr.id,
                    "messages": "Service Report information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR is existed!"
                })
        else:
            try:
                sr = Sr.objects.get(id=srid)
                sr.sr_no = sr_no
                sr.date = date
                sr.status = "Open"
                sr.created_by_id=request.user.id,
                # sr.uploaded_by_id=request.user.id
                sr.project_id = projectid
                sr.save()

                return JsonResponse({
                    "status": "Success",
                    "method": "update",
                    "newSrID": sr.id,
                    "messages": "Service Report information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR is existed!"
                })

@ajax_login_required
def pcadd(request):
    if request.method == "POST":
        pc_no = request.POST.get('pc_no')
        date = request.POST.get('pcdate')
        if date == "":
            date = None
        projectid = request.POST.get('projectid')
        pcid = request.POST.get('pcid')
        # if request.user.signature != "":
        #     status = "Signed"
        # else:
        #     status = "Open"
        if pcid == "-1":
            try:
                pc = Pc.objects.create(
                    pc_no=pc_no,
                    date=date,
                    status="Open",
                    # uploaded_by_id=request.user.id,
                    project_id=projectid,
                )
                return JsonResponse({
                    "status": "Success",
                    "method": "add",
                    "newPcID": pc.id,
                    "messages": "Progress Claim information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already PC is existed!"
                })
        else:
            try:
                pc = Pc.objects.get(id=pcid)
                pc.pc_no = pc_no
                pc.date = date
                # pc.status = "Open"
                # pc.uploaded_by_id=request.user.id
                pc.project_id = projectid
                pc.save()

                return JsonResponse({
                    "status": "Success",
                    "method": "update",
                    "newPcID": pc.id,
                    "messages": "Progress Claim information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already PC is existed!"
                })

@method_decorator(login_required, name='dispatch')
class SrDetailView(DetailView):
    model = Sr
    pk_url_kwarg = 'srpk'
    template_name="projects/service-report-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proj_pk = self.kwargs.get('pk')
        sr_pk = self.kwargs.get('srpk')
        summary = Project.objects.get(id=proj_pk)
        context['summary'] = summary
        context['project_pk'] = proj_pk
        context['service_pk'] = sr_pk
        service_report = Sr.objects.get(id=sr_pk)
        context['contacts'] = Contact.objects.all()
        context['uoms'] = Uom.objects.all()
        context['service_report'] = service_report
        quotation = Quotation.objects.get(qtt_id__iexact=summary.proj_id.replace('CPJ','').strip())
        context['sritems'] = SrItem.objects.filter(project_id=proj_pk, sr_id=sr_pk)
        context['quotation'] = quotation
        if(SRSignature.objects.filter(project_id=proj_pk, sr_id=sr_pk).exists()):
            context['srsignature'] = SRSignature.objects.get(project_id=proj_pk, sr_id=sr_pk)
        else:
            context['srsignature'] = None
        context['projectitemall'] = Scope.objects.filter(quotation_id=quotation.id)
        return context

@ajax_login_required
def ajax_update_service_report(request):
    if request.method == "POST":
        srtype = request.POST.get('srtype')
        srpurpose = request.POST.get('srpurpose')
        srsystem = request.POST.get('srsystem')
        timein = request.POST.get('timein')
        timeout = request.POST.get('timeout')
        remark = request.POST.get('remark')
        servicepk = request.POST.get('servicepk')

        srdata = Sr.objects.get(id=servicepk)
        srdata.srtype=srtype
        srdata.srpurpose=srpurpose
        srdata.srsystem =srsystem 
        srdata.time_in=date_parser.parse(timein).replace(tzinfo=pytz.utc)
        srdata.time_out=date_parser.parse(timeout).replace(tzinfo=pytz.utc)
        srdata.remark=remark
        srdata.save()

        return JsonResponse({
                "status": "Success",
                "messages": "Service Report information updated!"
            })

@ajax_login_required
def ajax_update_progress_claim(request):
    if request.method == "POST":
        pcclaimno = request.POST.get('pcclaimno')
        #terms = request.POST.get("terms")
        less_previous_claim = request.POST.get("less_previous_claim")
        progresspk = request.POST.get('progresspk')

        pcdata = Pc.objects.get(id=progresspk)
        pcdata.claim_no=int(pcclaimno)
        #pcdata.terms = terms
        pcdata.less_previous_claim = less_previous_claim
        pcdata.save()

        return JsonResponse({
                "status": "Success",
                "messages": "Progress Claim information updated!"
            })

@method_decorator(login_required, name='dispatch')
class SrSignatureCreate(generic.CreateView):
    model = SRSignature
    fields = '__all__'
    template_name="projects/service-signature.html"

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            SRSignature.objects.create(
                signature=request.POST.get('signature'),
                name=sign_name,
                nric = sign_nric,
                update_date = datetime.datetime.strptime(sign_date,'%d %b %Y'),
                sr_id=self.kwargs.get('srpk'),
                project_id=self.kwargs.get('pk')
            )
            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/service-report-detail/' + self.kwargs.get('srpk'))

@method_decorator(login_required, name='dispatch')
class SrSignatureUpdate(generic.UpdateView):
    model = SRSignature
    pk_url_kwarg = 'signpk'
    fields = '__all__'
    template_name="projects/service-signature.html"
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            srSignature = SRSignature.objects.get(id=self.kwargs.get('signpk'))
            srSignature.signature = request.POST.get('signature')
            srSignature.name = sign_name
            srSignature.nric = sign_nric
            srSignature.update_date = datetime.datetime.strptime(sign_date.replace(',', ""),'%d %b %Y').date()
            srSignature.sr_id = self.kwargs.get('srpk')
            srSignature.project_id = self.kwargs.get('pk')
            srSignature.save()

            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/service-report-detail/' + self.kwargs.get('srpk'))


@method_decorator(login_required, name='dispatch')
class PcDetailView(DetailView):
    model = Pc
    pk_url_kwarg = 'pcpk'
    template_name="projects/progress-claim-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proj_pk = self.kwargs.get('pk')
        pc_pk = self.kwargs.get('pcpk')
        summary = Project.objects.get(id=proj_pk)
        context['summary'] = summary
        context['project_pk'] = proj_pk
        context['progress_pk'] = pc_pk
        progress_claim = Pc.objects.get(id=pc_pk)
        context['contacts'] = Contact.objects.all()
        context['uoms'] = Uom.objects.all()
        context['progress_claim'] = progress_claim
        quotation = Quotation.objects.get(qtt_id__iexact=summary.proj_id.replace('CPJ','').strip())
        context['pcitems'] = PcItem.objects.filter(project_id=proj_pk, pc_id=pc_pk)
        context['quotation'] = quotation
        if PcItem.objects.filter(project_id=proj_pk, pc_id=pc_pk).exists():
            subtotal = PcItem.objects.filter(project_id=proj_pk, pc_id=pc_pk).aggregate(Sum('amount'))['amount__sum']
            gst = float(subtotal) * 0.07
            context['subtotal'] = subtotal
            context['gst'] = gst
            context['total_detail'] = float(subtotal) + gst
        if(PCSignature.objects.filter(project_id=proj_pk, pc_id=pc_pk).exists()):
            context['pcsignature'] = PCSignature.objects.get(project_id=proj_pk, pc_id=pc_pk)
        else:
            context['pcsignature'] = None
        context['projectitemall'] = Scope.objects.filter(quotation_id=quotation.id)
        return context

@method_decorator(login_required, name='dispatch')
class PcSignatureCreate(generic.CreateView):
    model = PCSignature
    fields = '__all__'
    template_name="projects/progress-signature.html"

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            PCSignature.objects.create(
                signature=request.POST.get('signature'),
                name=sign_name,
                nric = sign_nric,
                update_date = datetime.datetime.strptime(sign_date,'%d %b %Y'),
                pc_id=self.kwargs.get('pcpk'),
                project_id=self.kwargs.get('pk')
            )
            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/progress-claim-detail/' + self.kwargs.get('pcpk'))

@method_decorator(login_required, name='dispatch')
class PcSignatureUpdate(generic.UpdateView):
    model = PCSignature
    pk_url_kwarg = 'signpk'
    fields = '__all__'
    template_name="projects/progress-signature.html"
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            pcSignature = PCSignature.objects.get(id=self.kwargs.get('signpk'))
            pcSignature.signature = request.POST.get('signature')
            pcSignature.name = sign_name
            pcSignature.nric = sign_nric
            pcSignature.update_date = datetime.datetime.strptime(sign_date.replace(',', ""),'%d %b %Y').date()
            pcSignature.pc_id = self.kwargs.get('pcpk')
            pcSignature.project_id = self.kwargs.get('pk')
            pcSignature.save()

            return HttpResponseRedirect('/project-detail/' + self.kwargs.get('pk') + '/progress-claim-detail/' + self.kwargs.get('pcpk'))


@ajax_login_required
def pcItemAdd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        qty = request.POST.get('qty')
        uom = request.POST.get('uom')
        price = request.POST.get('price')
        done_qty = request.POST.get('done_qty')
        #done_percent = request.POST.get('done_percent')
        #amount = request.POST.get('amount')
        pcitemid = request.POST.get('pcitemid')
        projectid = request.POST.get('projectid')
        pcid = request.POST.get('pcid')

        if pcitemid == "-1":
            try:
                PcItem.objects.create(
                    description=description,
                    qty=qty,
                    uom_id=uom,
                    price=price,
                    done_qty=done_qty,
                    done_percent=round(100*float(done_qty)/float(qty), 2),
                    amount=float(price)*float(done_qty),
                    project_id=projectid,
                    pc_id=pcid
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Progress Claim Item information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already PC Item is existed!"
                })
        else:
            try:
                pcitem = PcItem.objects.get(id=pcitemid)
                pcitem.description = description
                pcitem.qty = qty
                pcitem.uom_id = uom
                pcitem.price=price
                pcitem.done_qty=done_qty
                pcitem.done_percent=round(100*float(done_qty)/float(qty), 2)
                pcitem.amount=float(price)*float(done_qty)
                pcitem.project_id = projectid
                pcitem.pc_id=pcid
                pcitem.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Progress Claim Item information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already PC Item is existed!"
                })

@ajax_login_required
def deletePCItem(request):
    if request.method == "POST":
        pcitem_del_id = request.POST.get('del_id')
        pcitem = PcItem.objects.get(id=pcitem_del_id)
        pcitem.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deleteSRItem(request):
    if request.method == "POST":
        sritem_del_id = request.POST.get('del_id')
        sritem = SrItem.objects.get(id=sritem_del_id)
        sritem.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def deleteDOItem(request):
    if request.method == "POST":
        doitem_del_id = request.POST.get('del_id')
        doitem = DoItem.objects.get(id=doitem_del_id)
        doitem.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def srItemAdd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        qty = request.POST.get('qty')
        uom = request.POST.get('uom')
        sritemid = request.POST.get('sritemid')
        projectid = request.POST.get('projectid')
        srid = request.POST.get('srid')

        if sritemid == "-1":
            try:
                SrItem.objects.create(
                    description=description,
                    qty=qty,
                    uom_id=uom,
                    project_id=projectid,
                    sr_id=srid
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Report Item information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR Item is existed!"
                })
        else:
            try:
                sritem = SrItem.objects.get(id=sritemid)
                sritem.description = description
                sritem.qty = qty
                sritem.uom_id = uom
                sritem.project_id = projectid
                sritem.sr_id=srid
                sritem.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Report Item information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR Item is existed!"
                })

@ajax_login_required
def doItemAdd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        qty = request.POST.get('qty')
        uom = request.POST.get('uom')
        doitemid = request.POST.get('doitemid')
        projectid = request.POST.get('projectid')
        doid = request.POST.get('doid')

        if doitemid == "-1":
            try:
                DoItem.objects.create(
                    description=description,
                    qty=qty,
                    uom_id=uom,
                    project_id=projectid,
                    do_id=doid
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Delivery Order Item information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already DO Item is existed!"
                })
        else:
            try:
                doitem = DoItem.objects.get(id=doitemid)
                doitem.description = description
                doitem.qty = qty
                doitem.uom_id = uom
                doitem.project_id = projectid
                doitem.do_id=doid
                doitem.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Delivery Order Item information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already DO Item is existed!"
                })

@ajax_login_required
def getDoItem(request):
    if request.method == "POST":
        doitemid = request.POST.get('doitemid')
        doitem = DoItem.objects.get(id=doitemid)
        data = {
            'description': doitem.description,
            'qty': doitem.qty,
            'uom': doitem.uom_id,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def getSrItem(request):
    if request.method == "POST":
        sritemid = request.POST.get('sritemid')
        sritem = SrItem.objects.get(id=sritemid)
        data = {
            'description': sritem.description,
            'qty': sritem.qty,
            'uom': sritem.uom_id,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def getPcItem(request):
    if request.method == "POST":
        pcitemid = request.POST.get('pcitemid')
        pcitem = PcItem.objects.get(id=pcitemid)
        data = {
            'description': pcitem.description,
            'qty': pcitem.qty,
            'uom': pcitem.uom_id,
            'price': pcitem.price,
            'done_qty': pcitem.done_qty,
            # 'done_percent': pcitem.done_percent,
            'amount': pcitem.amount,
        }
        return JsonResponse(json.dumps(data), safe=False)

def ajax_export_do_item(request, projectid, doid):
    resource = DoItemResource()
    queryset = DoItem.objects.filter(project_id=projectid, do_id=doid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project_do_items.csv"'
    return response

def ajax_export_sr_item(request, projectid, srid):
    resource = SrItemResource()
    queryset = SrItem.objects.filter(project_id=projectid, sr_id=srid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project_sr_items.csv"'
    return response

@ajax_login_required
def UpdateDeliveryOrder(request):
    if request.method == "POST":
        company_name = request.POST.get('company_name')
        address = request.POST.get('address')
        attn = request.POST.get('attn')
        tel = request.POST.get('tel')
        shipto = request.POST.get('shipto')
        proj_id = request.POST.get('proj_id')
        doid = request.POST.get('doid')

        try:
            delivery = Do.objects.get(id=doid)
            delivery.company_name=company_name
            delivery.address=address
            delivery.attn=attn
            delivery.tel=tel
            delivery.ship_to=shipto

            delivery.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Delivery Order information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@method_decorator(login_required, name='dispatch')
class BomDetailView(DetailView):
    model = Bom
    pk_url_kwarg = 'bompk'
    template_name="projects/bomlog-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proj_pk = self.kwargs.get('pk')
        bom_pk = self.kwargs.get('bompk')
        context['project_pk'] = proj_pk
        context['bom_pk'] = bom_pk
        context['uoms'] = Uom.objects.all()
        context['bom_logs'] = BomLog.objects.filter(bom_id=bom_pk)
        context['delivered_total'] = BomLog.objects.filter(bom_id=bom_pk, project_id=proj_pk).aggregate(Sum('delivered_qty'))['delivered_qty__sum']
        return context

@ajax_login_required
def subitemadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        uom = request.POST.get('uom')
        qty = request.POST.get('qty')
        allocation_perc = request.POST.get('allocation')
        quotationid = request.POST.get('quotationid')
        itemid = request.POST.get('itemid')
        Scope.objects.create(
            description=description,
            uom_id=uom,
            qty=qty,
            allocation_perc=allocation_perc,
            quotation_id=quotationid,
            parent_id=itemid,
        )
        #parent allocation_perc update
        parent = Scope.objects.get(id=itemid)
        allocation_sum = Scope.objects.filter(parent_id=itemid).aggregate(Sum('allocation_perc'))['allocation_perc__sum']
        parent.allocation_perc = allocation_sum
        parent.save()
        
        return JsonResponse({
            "status": "Success",
            "messages": "Scope Item information added!"
        })

@ajax_login_required
def getItem(request):
    if request.method == "POST":
        iid = request.POST.get('iid')
        item = Scope.objects.get(id=iid)
        data = {
            'description': item.description,
            'uom': item.uom,
            'qty': item.qty,
            'allocation': item.allocation_perc,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def getItemUom(request):
    if request.method == "POST":
        itemdescription = request.POST.get('itemdescription')
        quotationid = request.POST.get('quotationid')
        item = Scope.objects.get(quotation_id=quotationid, description__iexact=itemdescription)
        data = {
            'uom': item.uom_id,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def itemadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        uom = request.POST.get('uom')
        qty = request.POST.get('qty')
        allocation = request.POST.get('allocation')
        iid = request.POST.get('iid')
        
        try:
            scope = Scope.objects.get(id=iid)
            scope.description=description
            scope.uom_id=uom
            scope.qty=qty
            scope.allocation_perc=allocation
            
            scope.save()
            #parent allocation_perc update
            parent = Scope.objects.get(id=scope.parent_id)
            allocation_sum = Scope.objects.filter(parent_id=scope.parent_id).aggregate(Sum('allocation_perc'))['allocation_perc__sum']
            
            parent.allocation_perc = allocation_sum
            parent.save()
            return JsonResponse({
                "status": "Success",
                "messages": "Scope information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Already Scope is existed!"
            })   

@ajax_login_required
def siteprogressadd(request):
    if request.method == "POST":
        date = request.POST.get('date')
        description = request.POST.get('description')
        remark = request.POST.get('remark')
        qty = request.POST.get('qty')
        siteid = request.POST.get('siteid')
        projectid = request.POST.get('projectid')
        if siteid == "-1":
            try:
                SiteProgress.objects.create(
                    description=description,
                    remark=remark,
                    qty=qty,
                    date=date,
                    project_id=projectid
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Site Progress information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                siteprogress = SiteProgress.objects.get(id=siteid)
                siteprogress.description = description
                siteprogress.date = date
                siteprogress.remark = remark
                siteprogress.qty = qty
                siteprogress.project_id=projectid
                siteprogress.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Site Progress information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def getSiteProgress(request):
    if request.method == "POST":
        siteid = request.POST.get('siteid')
        site = SiteProgress.objects.get(id=siteid)
        data = {
            'description': site.description,
            'date': site.date.strftime('%d %b, %Y'),
            'remark': str(site.remark),
            'qty': site.qty
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def sitedelete(request):
    if request.method == "POST":
        siteid = request.POST.get('siteid')
        site = SiteProgress.objects.get(id=siteid)
        site.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def toolboxitemadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        objective = request.POST.get('objective')
        remark = request.POST.get('remark')
        activity = request.POST.get('activity')
        manager = request.POST.get('manager')
        projectid = request.POST.get('projectid')
        toolboxitemid = request.POST.get('toolboxid')
        
        if toolboxitemid == "-1":
            try:
                ToolBoxItem.objects.create(
                    activity=activity,
                    objective=objective,
                    remark=remark,
                    manager=manager,
                    description=description,
                    project_id=projectid,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "ToolBox Item information added!",
                    
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                tbmitem = ToolBoxItem.objects.get(id=toolboxitemid)
                tbmitem.activity = activity
                tbmitem.objective = objective
                tbmitem.remark = remark
                tbmitem.manager=manager
                tbmitem.description = description
                tbmitem.project_id = projectid
                tbmitem.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "ToolBox Item information updated!",
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def getToolBoxItem(request):
    if request.method == "POST":
        toolboxid = request.POST.get('toolboxid')
        tbmitem = ToolBoxItem.objects.get(id=toolboxid)
        data = {
            'activity': tbmitem.activity,
            'objective': tbmitem.objective,
            'description': tbmitem.description,
            'remark': tbmitem.remark,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def tbmitemdelete(request):
    if request.method == "POST":
        tbmitemid = request.POST.get('tbmitemdel_id')
        tbmitem = ToolBoxItem.objects.get(id=tbmitemid)
        tbmitem.delete()

        return JsonResponse({'status': 'ok'})

def exportSrPDF(request, value):
    sr = Sr.objects.get(id=value)
    project = sr.project
    quotation = project.quotation
    sritems = SrItem.objects.filter(sr_id=value)

    domain = request.META['HTTP_HOST']
    logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    response = HttpResponse(content_type='application/pdf')
    currentdate = datetime.date.today().strftime("%d-%m-%Y")
    pdfname = sr.sr_no + ".pdf"
    response['Content-Disposition'] = 'attachment; filename={}'.format(pdfname)
    story = []
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=portrait(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.25*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    data= [
        [Paragraph('''<para align=center><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Description</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>UOM</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>QTY</b></font></para>''')],
    ]

    if project.start_date:
        pdate =  project.start_date.strftime('%d %b, %Y')
    else:
        pdate = " "
    
    if quotation.company_name.country:
        country = quotation.company_name.country.name
    else:
        country = " "
    if quotation.company_name.unit:
        qunit = quotation.company_name.unit
    else:
        qunit = " "
    if sr.srpurpose:
        srpurpose = sr.srpurpose
    else:
        srpurpose = " "
    if sr.srsystem:
        srsystem = sr.srsystem
    else:
        srsystem = " "
    if sr.srtype:
        srtype = sr.srtype
    else:
        srtype = " "
    if sr.time_out:
        time_out = sr.time_out.strftime('%d/%m/%Y %H:%M')
    else:
        time_out = " "
    if sr.time_in:
        time_in = sr.time_in.strftime('%d/%m/%Y %H:%M')
    else:
        time_in = " "
    if sr.remark:
        srremark = sr.remark
    else:
        srremark = " "
    srinfordata = [
        [Paragraph('''<para align=left><font size=10><b>To: </b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.company_name)), "", "", "" , Paragraph('''<para align=center><font size=16><b>SERVICE REPORT</b></font></para>''')],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)),"", "", "" , ""],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)), "" ,"", "", Paragraph('''<para align=left><font size=10><b>SR No:</b> %s</font></para>''' % (sr.sr_no))],
        ["", "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Project No.:</b> %s</font></para>''' % (project.proj_id))],
        [Paragraph('''<para align=left><font size=10><b>Attn :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.contact_person.salutation + " " + project.contact_person.contact_person)),Paragraph('''<para align=left><font size=10><b>Email :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.email)), "", Paragraph('''<para align=left><font size=10><b>Date:</b> %s</font></para>''' % (sr.date.strftime('%d/%m/%Y')))],
        [Paragraph('''<para align=left><font size=10><b>Tel :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.tel)), Paragraph('''<para align=left><font size=10><b>Fax :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.fax)), "", ""],
        ["", "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10><b>Worksite: </b> %s</font></para>''' % (project.worksite_address)), "", "" ,"", "", ""],
        ["", "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10><b>Service Type: </b> %s</font></para>''' % (srtype)), "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Time In: </b> %s</font></para>''' % (time_in))],
        [Paragraph('''<para align=left><font size=10><b>System: </b> %s</font></para>'''  % (srsystem)), "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Time Out: </b> %s</font></para>''' % (time_out))],
        [Paragraph('''<para align=left><font size=10><b>Purpose: </b> %s</font></para>''' % (srpurpose)), "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10><b>Remark: </b></font></para>'''), "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10>%s</font></para>''' % (srremark)), "", "" ,"", "", ""],
    ]
    sr_head = ParagraphStyle("justifies", leading=18)
    information = Table(
        srinfordata,
        style=[
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(-1,0),'BOTTOM'),
            ('SPAN', (0, -3), (1, -3)),
            ('ALIGN',(5,0),(5,-1),'CENTER'),
            ('SPAN',(1,1),(3,1)),
            ('SPAN',(1,2),(3,2)),
            ('SPAN',(3,4),(4,4)),
            ('SPAN',(0,7),(-1,7)),
            ('SPAN',(0,9),(-2,9)),
            ('SPAN',(0,10),(-2,10)),
            ('SPAN',(0,11),(-1,11)),
            ('SPAN',(0,13),(-1,13)),

        ]
    )
    
    information._argW[0]=0.8*inch
    information._argW[1]=1.28*inch
    information._argW[2]=0.8*inch
    information._argW[3]=1.38*inch
    information._argW[4]=0.89*inch
    information._argW[5]=2.17*inch
    story.append(Spacer(1, 16))
    story.append(information)
    story.append(Spacer(1, 16))
    index = 1
    if sritems.exists():
        for sritem in sritems:
            temp_data = []
            description = '''
                <para align=center>
                    %s
                </para>
            ''' % (str(sritem.description))
            pdes = Paragraph(description, styleSheet["BodyText"])
            temp_data.append(str(index))
            temp_data.append(pdes)
            temp_data.append(str(sritem.uom))
            temp_data.append(str(sritem.qty))
            data.append(temp_data)
            index += 1

        exportD=Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (5, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ],
        )
    else:
        data.append(["No data available in table", "", "", ""]) 
        exportD = Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('SPAN',(0,1),(-1,-1)),
            ],
        )
        exportD._argH[1]=0.3*inch
    exportD._argW[0]=0.40*inch
    exportD._argW[1]=5.456*inch
    exportD._argW[2]=0.732*inch
    exportD._argW[3]=0.732*inch
    story.append(exportD)
    story.append(Spacer(1, 15))
    if len(data) > 6:
        story.append(PageBreak())
        story.append(Spacer(1, 15))

    style_condition = ParagraphStyle(name='left',fontSize=9, parent=styleSheet['Normal'], leftIndent=20, leading=15)
    story.append(Paragraph("Received the above Goods in Good Order & Condition", style_condition))
    
    story.append(Spacer(1, 10))
    
    style_sign = ParagraphStyle(name='left',fontSize=10, parent=styleSheet['Normal'])
    sign_title1 = '''
        <para align=left>
            <font size=10><b>Signature: </b></font>
        </para>
    '''
    sign_title2 = '''
        <para align=left>
            <font size=10><b>Authorised  Signature: </b></font>
        </para>
    '''
    
    srtable1=Table(
        [
            [Paragraph('''<para align=left><font size=12><b>For Customers:</b></font></para>'''), Paragraph('''<para align=right><font size=12><b>For CNI TECHNOLOGY PTE LTD:</b></font></para>''')],
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    srtable1._argW[0]=3.66*inch
    srtable1._argW[1]=3.66*inch
    story.append(srtable1)
    srsignature = SRSignature.objects.filter(sr_id=value)
    
    if srsignature.exists():
        srsign_data = SRSignature.objects.get(sr_id=value)
        sign_name = srsign_data.name
        sign_nric = srsign_data.nric
        sign_date = srsign_data.update_date.strftime('%d/%m/%Y')
        sign_logo = Image('http://' + domain + srsign_data.signature_image.url, hAlign='LEFT', width=1.2*inch, height=0.8*inch)
            
    else:
        sign_name = ""
        sign_nric = ""
        sign_date = ""
        sign_logo = ""

    if sr.created_by:
        if sr.created_by.signature:
            auto_sign = Image('http://' + domain + sr.created_by.signature.url, hAlign='LEFT', width=0.8*inch, height=0.8*inch)
        else:
            auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    else:
        auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    srtable3=Table(
        [
            [Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_name)), "",Paragraph(sign_title2, style_sign), ""],
            [Paragraph(sign_title1, style_sign), "", "", auto_sign, ""],
            ["", sign_logo,"", "", ""]
        ],
        style=[
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('SPAN',(3,0),(-1,0)),
            ('SPAN',(3,1),(4,-1)),
            ('SPAN',(1,2),(2,2)),
        ],
    )
    story.append(Spacer(1, 10))
    srtable3._argW[0]=1.0*inch
    srtable3._argW[1]=1.83*inch
    srtable3._argW[2]=1.63*inch
    srtable3._argW[3]=1.0*inch
    srtable3._argW[4]=1.83*inch
    story.append(srtable3)
    srtable4=Table(
        [
            [Paragraph('''<para align=left spaceb=2><font size=9><b>NRIC</b></font><br/><font size=9><b>(last 3 digits):</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_nric))],
            [Paragraph('''<para align=left><font size=9><b>Date:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_date))]
        ],
        style=[
            ('VALIGN',(1,0),(1,-1),'MIDDLE'),
        ],
    )
    srtable4._argW[0]=1.0*inch
    srtable4._argW[1]=6.32*inch
    story.append(Spacer(1, 10))
    story.append(srtable4)
    doc.build(story,canvasmaker=NumberedCanvas)
    response.write(buff.getvalue())
    buff.close()

    return response

def exportPcPDF(request, value):
    pc = Pc.objects.get(id=value)
    project = pc.project
    domain = request.META['HTTP_HOST']
    response = HttpResponse(content_type='application/pdf')
    currentdate = datetime.date.today().strftime("%d-%m-%Y")
    pdfname = pc.pc_no + ".pdf"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(pdfname)
    story = []
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=landscape(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.5*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    
    story.append(Spacer(1, 16))
    if pc.claim_no:
        claimno = pc.claim_no
    else:
        claimno = ""
    quotation = project.quotation
    if quotation.company_name.unit:
        qunit = quotation.company_name.unit
    else:
        qunit = ""
    if quotation.sale_person:
        qsale_person = quotation.sale_person
    else:
        qsale_person = ""

    if quotation.terms:
        qterms = quotation.terms
    else:
        qterms = ""
    if quotation.po_no:
        qpo_no = quotation.po_no
    else:
        qpo_no = ""
    pcindata = [
        [Paragraph('''<para align=left><font size=10><b>To: </b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.company_name)), "", "", "" , Paragraph('''<para align=center><font size=16><b>PROGRESS CLAIM</b></font></para>''')],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)),"", "", "" , ""],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)), "" ,"", "", Paragraph('''<para align=left><font size=10>Pc No: %s</font></para>''' % (pc.pc_no))],
        ["", "", "" ,"", "", Paragraph('''<para align=left><font size=10>Project No.: %s</font></para>''' % (project.proj_id))],
        [Paragraph('''<para align=left><font size=10><b>Attn :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.contact_person.salutation + " " + project.contact_person.contact_person)),Paragraph('''<para align=left><font size=10><b>Email :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.email)), "", Paragraph('''<para align=left><font size=10>Sales: %s</font></para>''' % (qsale_person))],
        [Paragraph('''<para align=left><font size=10><b>Tel :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.tel)), Paragraph('''<para align=left><font size=10><b>Fax :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (project.fax)), "", Paragraph('''<para align=left><font size=10>Terms: %s Days</font></para>''' % (qterms))],
        ["", "", "" ,"", "", Paragraph('''<para align=left><font size=10>PO No.: %s</font></para>''' % (qpo_no))],
        [Paragraph('''<para align=left><font size=10><b>Project:</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' %(project.RE)), "" ,"", "", Paragraph('''<para align=left><font size=10>Date Prepared: %s</font></para>''' % (pc.date.strftime("%d/%m/%Y")))],
        ["", "", "" ,"", "", Paragraph('''<para align=left><font size=10>Prog. Claim No: %s</font></para>''' % (claimno))],
    ]
    pcintable = Table(
        pcindata,
        style=[
            ('VALIGN',(-1,0),(-1,0),'TOP'),
            ('ALIGN',(-1,0),(-1,0),'CENTER'),
            ('SPAN',(-1,0),(-1,1)),
            ('SPAN',(3,4),(4,4)),
            ('SPAN',(1,7),(4,7)),
            ('SPAN',(1,2),(4,2)),
            ('SPAN',(1,1),(4,1)),
        ],
    )
    pcintable._argW[0]=0.7*inch
    pcintable._argW[1]=1.28*inch
    pcintable._argW[2]=0.7*inch
    pcintable._argW[3]=1.28*inch
    pcintable._argW[4]=4.568*inch
    pcintable._argW[5]=2.27*inch
    pcintable._argH[0]=0.2*inch
    pcintable._argH[1]=0.2*inch
    pcintable._argH[2]=0.2*inch
    pcintable._argH[3]=0.2*inch
    pcintable._argH[4]=0.2*inch
    pcintable._argH[5]=0.2*inch
    pcintable._argH[6]=0.2*inch
    pcintable._argH[7]=0.2*inch
    pcintable._argH[8]=0.2*inch
    story.append(pcintable)
    story.append(Spacer(1, 10))
    pc_data= [
        [Paragraph('''<para align=center><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Description</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>QTY</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>UOM</b></font></para>'''),Paragraph('''<para align=center><font size=10><b>Percentage</b></font></para>'''), Paragraph('''<para align=center spaceb=2><font size=10><b>Unit Rate</b></font></para>'''),
        Paragraph('''<para align=center spaceb=2><font size=10><b>Sub</b></font><br/><font size=10><b>Amount</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Current Claim</b></font></para>'''), "",Paragraph('''<para align=center><font size=10><b>Cumulative Claim</b></font></para>'''), ""
        ],
        ["", "", "", "", "", "","",
        Paragraph('''<para align=center spaceb=2><font size=10><b>Work Done</b></font><br/><font size=10><b>(Qty)</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Total Amount</b></font></para>'''),
        Paragraph('''<para align=center spaceb=2><font size=10><b>Work Done</b></font><br/><font size=10><b>(Qty)</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Total Amount</b></font></para>''')
        ],
    ]
    pcitems = PcItem.objects.filter(pc_id=value)
    total_pcworkdone_qty = 0
    index = 1
    if pcitems.exists():
        
        for pcitem in pcitems:
            total_pcworkdone_qty += float(pcitem.done_qty) * float(pcitem.price)
            temp_data = []
            description = '''
                <para align=center>
                    %s
                </para>
            ''' % (str(pcitem.description))
            pcdes = Paragraph(description, styleSheet["BodyText"])
            pcdone_qty = str(pcitem.done_qty)
            pcworkdone_qty = "$ " + '{0:.2f}'.format(float(pcitem.done_qty) * float(pcitem.price))
            pcunit = "$ " + '{0:.2f}'.format(float(pcitem.price))
            pcsub_amount = "$ " + '{0:.2f}'.format(float(pcitem.price))
            temp_data.append(str(index))
            temp_data.append(pcdes)
            temp_data.append(str(pcitem.qty))
            temp_data.append(str(pcitem.uom))
            temp_data.append(str(pcitem.done_percent) + " %")
            temp_data.append(pcunit)
            temp_data.append(pcsub_amount)
            temp_data.append(Paragraph('''<para align=center><font size=10>%s</font></para>''' % (pcdone_qty)))
            temp_data.append(Paragraph('''<para align=center><font size=10>%s</font></para>''' % (pcworkdone_qty)))
            temp_data.append("")
            temp_data.append("")
            pc_data.append(temp_data)
            index += 1
        total_pc_gst = total_pcworkdone_qty * 0.07
        statistic = []
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append(Paragraph('''<para align=left><font size=9><b>TOTAL</b></font></para>'''))
        statistic.append("$ " + '%.2f' % float(total_pcworkdone_qty))
        statistic.append("")
        statistic.append("")
        pc_data.append(statistic)
        statistic = []
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append(Paragraph('''<para align=left><font size=9><b>GST 7%</b></font></para>'''))
        statistic.append("$ " + '%.2f' % float(total_pc_gst))
        statistic.append("")
        statistic.append("")
        pc_data.append(statistic)
        statistic = []
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append(Paragraph('''<para align=left><font size=9><b>FINAL TOTAL</b></font></para>'''))
        statistic.append("$ " + '%.2f' % (float(total_pcworkdone_qty) + float(total_pc_gst)))
        statistic.append("")
        statistic.append("")
        pc_data.append(statistic)
        pctable = Table(
            pc_data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 1), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('SPAN',(0,0),(0,1)),
                ('SPAN',(1,0),(1,1)),
                ('SPAN',(2,0),(2,1)),
                ('SPAN',(3,0),(3,1)),
                ('SPAN',(4,0),(4,1)),
                ('SPAN',(5,0),(5,1)),
                ('SPAN',(6,0),(6,1)),
                ('SPAN',(7,0),(8,0)),
                ('SPAN',(9,0),(10,0)),
            ],
        )
    else:
        pc_data.append(["No data available in table", "","","", "", "", "", "","", "",""])
        pctable = Table(
            pc_data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 1), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('SPAN',(0,0),(0,1)),
                ('SPAN',(1,0),(1,1)),
                ('SPAN',(2,0),(2,1)),
                ('SPAN',(3,0),(3,1)),
                ('SPAN',(4,0),(4,1)),
                ('SPAN',(5,0),(5,1)),
                ('SPAN',(6,0),(6,1)),
                ('SPAN',(7,0),(8,0)),
                ('SPAN',(9,0),(10,0)),
                ('SPAN',(0,2),(-1,-1)),
            ],
        )
        pctable._argH[2]=0.4*inch
        
    pctable._argW[0]=0.40*inch
    pctable._argW[1]=2.888*inch
    pctable._argW[2]=0.60*inch
    pctable._argW[3]=0.60*inch
    pctable._argW[4]=1.0*inch
    pctable._argW[5]=0.60*inch
    pctable._argW[6]=0.70*inch
    pctable._argW[7]=1.0*inch
    pctable._argW[8]=1.0*inch
    pctable._argW[9]=1.0*inch
    pctable._argW[10]=1.0*inch
    story.append(pctable)
    story.append(Spacer(1, 10))
    if len(pc_data) < 4:
        story.append(PageBreak())
        story.append(Spacer(1, 15))
    style_sign = ParagraphStyle(name='left',fontSize=10, parent=styleSheet['Normal'])
    if pc.less_previous_claim:
        less_previous_claim = pc.less_previous_claim
        pccurrent = Table(
            [
                [Paragraph('''<para align=left><font size=10><b>Current Claim Amount:</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % ("$ " + '%.2f' % (total_pcworkdone_qty * 1.07)))],
                [Paragraph('''<para align=left><font size=10><b>Less Previous Claim:</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % ("$ " + '%.2f' % float(less_previous_claim)))]
            ],
            style=[
                ('VALIGN',(0,0),(1,0),'MIDDLE'),
                ('ALIGN',(0,0),(1,0),'LEFT'),
            ],
        )
    else:
        less_previous_claim = ""
        pccurrent = Table(
            [
                [Paragraph('''<para align=left><font size=10><b>Current Claim Amount:</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % ("$ " + '%.2f' % (total_pcworkdone_qty * 1.07)))],
                [Paragraph('''<para align=left><font size=10><b>Less Previous Claim:</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (""))]
            ],
            style=[
                ('VALIGN',(0,0),(1,0),'MIDDLE'),
                ('ALIGN',(0,0),(1,0),'LEFT'),
            ],
        )
    pccurrent._argW[0]=1.888*inch
    pccurrent._argW[1]=8.9*inch
    story.append(pccurrent)
    story.append(Spacer(1, 10))
    sign_title1 = '''
        <para align=left>
            <font size=10><b>Signature: </b></font>
        </para>
    '''
    sign_title2 = '''
        <para align=left>
            <font size=10><b>Signature: </b></font>
        </para>
    '''
    if request.user.signature:
        sign_logo = Image('http://' + domain + request.user.signature.url, width=0.8*inch, height=0.8*inch, hAlign='LEFT')
    else:
        sign_logo = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    pctable1=Table(
        [
            [Paragraph('''<para align=left><font size=12><b>Prepared By:</b></font></para>'''),"", "", Paragraph('''<para align=left><font size=12><b>Certified By:</b></font></para>''')],
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    pctable1._argW[0]=2.394*inch
    pctable1._argW[1]=2.50*inch
    pctable1._argW[2]=2.50*inch
    pctable1._argW[3]=3.394*inch
    story.append(pctable1)
    pctable2=Table(
        [
            [Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (request.user.first_name)),"", Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9></font></para>''')]
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    pctable2._argW[0]=0.8*inch
    pctable2._argW[1]=2.994*inch
    pctable2._argW[2]=3.6*inch
    pctable2._argW[3]=0.8*inch
    pctable2._argW[4]=2.594*inch
    story.append(Spacer(1, 10))
    story.append(pctable2)
    if pc.uploaded_by:
        if pc.uploaded_by.signature:
            auto_sign = Image('http://' + domain + pc.uploaded_by.signature.url, hAlign='LEFT')
        else:
            auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    else:
        auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    pctable3=Table(
        [
            [Paragraph(sign_title1, style_sign), "", "", Paragraph(sign_title2, style_sign), ""],
            ["", sign_logo,"", "", ""]
        ],
        style=[
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('SPAN',(3,1),(4,-1)),
        ],
    )
    story.append(Spacer(1, 10))
    pctable3._argW[0]=1.0*inch
    pctable3._argW[1]=2.794*inch
    pctable3._argW[2]=3.6*inch
    pctable3._argW[3]=1.0*inch
    pctable3._argW[4]=2.394*inch
    story.append(pctable3)
   
    doc.build(story,canvasmaker=LandScapeNumberedCanvas)
    response.write(buff.getvalue())
    buff.close()

    return response

def exportDoPDF(request, value):
    do = Do.objects.get(id=value)
    project = do.project
    quotation = project.quotation
    doitems = DoItem.objects.filter(do_id=value)
    domain = request.META['HTTP_HOST']
    logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    response = HttpResponse(content_type='application/pdf')
    currentdate = datetime.date.today().strftime("%d-%m-%Y")
    pdfname = do.do_no + ".pdf"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(pdfname)
    
    story = []
    data= [
        [Paragraph('''<para align=center><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Description</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>UOM</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>QTY</b></font></para>''')],
    ]
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=portrait(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.25*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    
    doinformation = []
    if do.date:
        dodate =  do.date.strftime('%d/%m/%Y')
    else:
        dodate = " "
    if quotation.sale_person:
        qsale_person = quotation.sale_person
    else:
        qsale_person = ""
    if quotation.terms:
        qterms = str(quotation.terms) + " Days"
    else:
        qterms = ""
    if quotation.po_no:
        qpo_no = quotation.po_no
    else:
        qpo_no = ""
    do_title1 = '''
        <para align=right>
            <font size=16><b>DELIVERY ORDER</b></font><br/>
        </para>
    '''
    do_title2 = '''
        <para align=left>
            <font size=10>DO No: %s</font><br/>
            <font size=10>Project No: %s</font><br/>
            <font size=10>Date: %s</font><br/>
            
        </para>
    ''' % (do.do_no, project.proj_id, dodate)
    do_title3 = '''
        <para align=left>
            <font size=10>Sales: %s</font><br/>
            <font size=10>Terms: %s</font><br/>
            <font size=10>Po No: %s</font><br/>
            
        </para>
    ''' % (qsale_person, qterms, qpo_no)
    
    if Quotation.objects.filter(qtt_id__iexact=project.qtt_id).exists():
        quotation = Quotation.objects.get(qtt_id__iexact=project.qtt_id)
        if quotation.company_name.country:
            country = quotation.company_name.country.name
        else:
            country = " "
        if quotation.company_name.unit:
            qunit = quotation.company_name.unit
        else:
            qunit = " "
        if quotation.company_name.postal_code != "":
            postalcode = quotation.company_name.postal_code
        else:
            postalcode = " "
            
        bill_to2 = '''
            <para align=left>
                <font size=10>%s</font><br/>
                <font size=10>%s</font>
            </para> 
        ''' % (quotation.address + " " + str(qunit), str(country) + " " + str(postalcode))
    else:
        bill_to2 = '''
            <para align=left>
                <font size=10>%s</font><br/>
                <font size=10>%s</font>
            </para> 
        ''' % ("", "")
    bill_to1 = '''
        <para align=left>
            <font size=10>%s</font><br/>
        </para> 
    ''' % (project.company_name)
    
    b_to = '''
        <para align=left>
            <font size=10>Bill To: </font>
        </para>
    '''
    do_head = ParagraphStyle("justifies", leading=18)
    doinformation.append([Paragraph(b_to), Paragraph(bill_to1), "", Paragraph(do_title1, do_head)])
    information = Table(
        doinformation,
        style=[
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(-1,0),'BOTTOM'),
        ]
    )
    
    information._argW[0]=0.8*inch
    information._argW[1]=3.0*inch
    information._argW[2]=0.52*inch
    information._argW[3]=3.0*inch
    story.append(Spacer(1, 16))
    story.append(information)
    doinformation1 = []
    doinformation1.append(["", Paragraph(bill_to2,do_head), "", Paragraph(do_title2, do_head)])
    information1 = Table(
        doinformation1,
        style=[
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(1,0),'TOP')
        ]
    )
    
    information1._argW[0]=0.8*inch
    information1._argW[1]=3.0*inch
    information1._argW[2]=1.52*inch
    information1._argW[3]=2.0*inch
    story.append(information1)
    if do.ship_to:
        shipto = do.ship_to
    else:
        shipto = ""
    ship_to = '''
        <para align=left>
            <font size=10>%s</font>
        </para> 
    ''' % (shipto)
    s_to = '''
        <para align=left>
            <font size=10>Ship To: </font>
        </para>
    '''
    shipinformation = []
    shipinformation.append([Paragraph(s_to), Paragraph(ship_to, do_head),"", Paragraph(do_title3, do_head)])
    sinformation = Table(
        shipinformation,
        style=[
            ('ALIGN',(0,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]
    )
    
    sinformation._argW[0]=0.8*inch
    sinformation._argW[1]=3.0*inch
    sinformation._argW[2]=1.52*inch
    sinformation._argW[3]=2.0*inch
    story.append(sinformation)
    
    infordetail = []
    do_attn = '''
        <para align=left>
            <font size=10>Attn:  %s</font>
        </para>
    ''' % (project.contact_person.salutation + " " + project.contact_person.contact_person)
    project_tel = '''
        <para align=left>
            <font size=10>Tel:  %s</font>
        </para>
    ''' % (project.tel)
    
    infordetail.append([Paragraph(do_attn), Paragraph(project_tel), ""])
    infor = Table(
        infordetail,
        style=[
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(-1,0),'TOP'),
        ]
    )
    
    infor._argW[0]=2.0*inch
    infor._argW[1]=2.5*inch
    infor._argW[2]=2.82*inch
    infor._argH[0]=0.32*inch
    story.append(infor)
    story.append(Spacer(1,15))
    if doitems.exists():
        index = 1
        for doitem in doitems:
            temp_data = []
            description = '''
                <para align=center>
                    %s
                </para>
            ''' % (str(doitem.description))
            pddes = Paragraph(description, styleSheet["BodyText"])
            temp_data.append(str(index))
            temp_data.append(pddes)
            temp_data.append(str(doitem.uom))
            temp_data.append(str(doitem.qty))
            data.append(temp_data)
            index += 1
        exportD=Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (5, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ],
        )
    else:
        data.append(["No data available in table", "", "", ""]) 
        exportD = Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('SPAN',(0,1),(-1,-1)),
            ],
        )
        exportD._argH[1]=0.3*inch

    
    exportD._argW[0]=0.40*inch
    exportD._argW[1]=5.456*inch
    exportD._argW[2]=0.732*inch
    exportD._argW[3]=0.732*inch
    story.append(exportD)
    story.append(Spacer(1, 15))
    style_condition = ParagraphStyle(name='left',fontSize=9, parent=styleSheet['Normal'], leftIndent=20, leading=15)
    story.append(Paragraph("Received the above Goods in Good Order & Condition", style_condition))
    story.append(Paragraph("Please be informed that unless payment is received in full, CNI Technology Pte Ltd will remain as the rightful owner of the delivered equipment(s)/material(s) on site.", style_condition))
    
    story.append(Spacer(1, 10))
    if len(data) > 6:
        story.append(PageBreak())
        story.append(Spacer(1, 15))
    dosignature = DOSignature.objects.filter(do_id=value)
    
    if dosignature.exists():
        dosign_data = DOSignature.objects.get(do_id=value)
        sign_name = dosign_data.name
        sign_nric = dosign_data.nric
        sign_date = dosign_data.update_date.strftime('%d/%m/%Y')
        sign_logo = Image('http://' + domain + dosign_data.signature_image.url, width=1.2*inch, height=0.8*inch, hAlign='LEFT')
            
    else:
        sign_name = ""
        sign_nric = ""
        sign_date = ""
        sign_logo = ""
    if do.created_by:
        if do.created_by.signature:
            auto_sign = Image('http://' + domain + do.created_by.signature.url,width=0.8*inch, height=0.8*inch, hAlign='LEFT')
        else:
            auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    else:
        auto_sign = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')

    style_sign = ParagraphStyle(name='left',fontSize=10, parent=styleSheet['Normal'])
    sign_title1 = '''
        <para align=left>
            <font size=10><b>Signature: </b></font>
        </para>
    '''
    sign_title2 = '''
        <para align=left>
            <font size=10><b>Authorised  Signature: </b></font>
        </para>
    '''
    dotable1=Table(
        [
            [Paragraph('''<para align=left><font size=12><b>For Customers:</b></font></para>'''), Paragraph('''<para align=right><font size=12><b>For CNI TECHNOLOGY PTE LTD:</b></font></para>''')],
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    dotable1._argW[0]=3.66*inch
    dotable1._argW[1]=3.66*inch
    story.append(dotable1)
    dotable3=Table(
        [
            [Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_name)), "",Paragraph(sign_title2, style_sign), ""],
            [Paragraph(sign_title1, style_sign), "", "", auto_sign, ""],
            ["", sign_logo,"", "", ""]
        ],
        style=[
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('SPAN',(3,0),(-1,0)),
            ('SPAN',(3,1),(4,-1)),
        ],
    )
    story.append(Spacer(1, 10))
    dotable3._argW[0]=1.0*inch
    dotable3._argW[1]=1.83*inch
    dotable3._argW[2]=1.63*inch
    dotable3._argW[3]=1.0*inch
    dotable3._argW[4]=1.83*inch
    story.append(dotable3)
    dotable4=Table(
        [
            [Paragraph('''<para align=left spaceb=2><font size=9><b>NRIC</b></font><br/><font size=9><b>(last 3 digits):</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_nric))],
            [Paragraph('''<para align=left><font size=9><b>Date:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (sign_date))]
        ],
        style=[
            ('VALIGN',(1,0),(1,-1),'MIDDLE'),
        ],
    )
    dotable4._argW[0]=1.0*inch
    dotable4._argW[1]=6.32*inch
    story.append(Spacer(1, 10))
    story.append(dotable4)
    doc.build(story,canvasmaker=NumberedCanvas)
    
    response.write(buff.getvalue())
    buff.close()
    return response

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.PAGE_HEIGHT=defaultPageSize[1]
        self.PAGE_WIDTH=defaultPageSize[0]
        self.domain = settings.HOST_NAME
        self.logo = ImageReader('http://' + self.domain + '/static/assets/images/printlogo.png')

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.drawImage(self.logo, 50, self.PAGE_HEIGHT - 100, width=70, height=70, mask='auto')
        self.setFont("Helvetica-Bold", 16)
        self.drawString(150, self.PAGE_HEIGHT - 50, "CNI TECHNOLOGYPTE LTD")
        self.setFont("Helvetica", 10)
        self.drawString(150, self.PAGE_HEIGHT - 65, "Block 3023 Ubi Road 3, #02-15 Ubi Plex 1, Singapore 408663")
        self.drawString(150, self.PAGE_HEIGHT - 80, "Tel.6747 6169 Fax.7647 5669")
        self.drawString(150, self.PAGE_HEIGHT - 95, "RCB No.201318779M")
        self.setFont("Times-Roman", 9)
        self.drawRightString(self.PAGE_WIDTH/2.0 + 10, 0.35 * inch,
            "Page %d of %d" % (self._pageNumber, page_count))

class LandScapeNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.PAGE_HEIGHT=defaultPageSize[0]
        self.PAGE_WIDTH=defaultPageSize[1]
        self.domain = settings.HOST_NAME
        self.logo = ImageReader('http://' + self.domain + '/static/assets/images/printlogo.png')

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.drawImage(self.logo, 50, self.PAGE_HEIGHT - 100, width=70, height=70, mask='auto')
        self.setFont("Helvetica-Bold", 16)
        self.drawString(150, self.PAGE_HEIGHT - 50, "CNI TECHNOLOGYPTE LTD")
        self.setFont("Helvetica", 10)
        self.drawString(150, self.PAGE_HEIGHT - 65, "Block 3023 Ubi Road 3, #02-15 Ubi Plex 1, Singapore 408663")
        self.drawString(150, self.PAGE_HEIGHT - 80, "Tel.6747 6169 Fax.7647 5669")
        self.drawString(150, self.PAGE_HEIGHT - 95, "RCB No.201318779M")
        self.setFont("Times-Roman", 9)
        self.drawRightString(self.PAGE_WIDTH/2.0 + 10, 0.35 * inch,
            "Page %d of %d" % (self._pageNumber, page_count))