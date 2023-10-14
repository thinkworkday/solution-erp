import random
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http.response import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from sales.models import Company, Payment, Quotation, SaleReport, SaleReportComment, Contact, Scope, Signature, QFile, Validity
from cities_light.models import Country
from accounts.models import Privilege, Uom, User, Role
from django.http import JsonResponse
from django.db import IntegrityError
import json
from sales.decorater import ajax_login_required, sale_report_privilege_required
from datetime import date
from django.views.generic.detail import DetailView
import datetime
import pytz
from reportlab.platypus import SimpleDocTemplate, Table, Image, Spacer, TableStyle, PageBreak, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.pdfgen import canvas
from reportlab.rl_config import defaultPageSize
from reportlab.lib.utils import ImageReader
import xlwt
from project.models import Project
from maintenance.models import Maintenance
import time
from notifications.signals import notify
from django.db.models import Sum
from decimal import Decimal
from sales.resources import CompanyResource, ContactResource
import pandas as pd
import os
from django.db.models import Q
from funky_sheets.formsets import HotView

# Create your views here.
@method_decorator(login_required, name='dispatch')
class CompanyList(ListView):
    model = Company
    template_name = "sales/company/company-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countrys'] = Country.objects.all()
        context['companies'] = Company.objects.order_by('name').values('name').distinct()
        
        return context
@ajax_login_required
def contactCompanyAdd(request):
    if request.method == "POST":
        name = request.POST.get('name')
        address = request.POST.get('address')
        unit = request.POST.get('unit')
        postalcode = request.POST.get('postalcode')
        country = request.POST.get('country')
        associate = request.POST.get('associate')
        comid = request.POST.get('comid')
        try:
            company = Company.objects.create(
                name=name,
                address=address,
                unit=unit,
                postal_code=postalcode,
                country_id=country,
                associate=associate,
            )
            return JsonResponse({
                "status": "Success",
                "messages": "Company information added!",
                'companyid': company.id,
                'companyname': company.name
            })
        except IntegrityError as e: 
            return JsonResponse({
                "status": "Error",
                "messages": "Already this Company is existed!"
            })

@ajax_login_required
def ajax_export_company(request):
    resource = CompanyResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="company.csv"'
    return response

def ajax_import_company(request):
    
    if request.method == 'POST':
        org_column_names = ["name", "address", "unit",  "postal_code", "associate"]
        
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
                exist_count = Company.objects.filter(name=row["name"]).count()
                if exist_count == 0:
                    try:
                        company = Company(
                            name=row["name"],
                            address=row["address"],
                            unit=row["unit"],
                            postal_code=row["postal_code"],
                            associate=row["associate"],
                        )
                        company.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        company = Company.objects.filter(name=row["name"])[0]
                        company.name = row["name"]
                        company.address = row["address"]
                        company.unit=str(row["unit"])
                        company.postal_code=row["postal_code"]
                        company.associate=row["part_number"]
                        
                        company.save()
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

def ajax_export_contact(request):
    resource = ContactResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contact.csv"'
    return response

def ajax_import_contact(request):
    
    if request.method == 'POST':
        org_column_names = ["contact_person", "tel", "fax",  "email", "role"]
        
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
                exist_count = Contact.objects.filter(contact_person=row["contact_person"]).count()
                if exist_count == 0:
                    try:
                        contact = Contact(
                            contact_person=row["contact_person"],
                            tel=row["tel"],
                            fax=row["fax"],
                            email=row["email"],
                            role=row["role"],
                        )
                        contact.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        contact = Contact.objects.filter(contact_person=row["contact_person"])[0]
                        contact.contact_person = row["contact_person"]
                        contact.tel = row["tel"]
                        contact.fax=row["fax"]
                        contact.email=row["email"]
                        contact.role=row["role"]
                        
                        contact.save()
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
def companyadd(request):
    if request.method == "POST":
        name = request.POST.get('name')
        address = request.POST.get('address')
        unit = request.POST.get('unit')
        postalcode = request.POST.get('postalcode')
        country = request.POST.get('country')
        associate = request.POST.get('associate')
        comid = request.POST.get('comid')
        if comid == "-1":
            try:
                company = Company.objects.create(
                    name=name,
                    address=address,
                    unit=unit,
                    postal_code=postalcode,
                    country_id=country,
                    associate=associate,
                    payment_id = Payment.objects.all().order_by('id')[0].id,
                    validity_id=Validity.objects.all().order_by('id')[0].id
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Company information added!",
                    "companyId": company.id
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already this Company is existed!"
                })
        else:
            try:
                company = Company.objects.get(id=comid)
                company.name = name
                company.address = address
                company.unit = unit
                company.postal_code = postalcode
                company.country_id = country
                company.associate = associate
                company.payment_id = Payment.objects.all().order_by('id')[0].id
                company.validity_id = Validity.objects.all().order_by('id')[0].id
                company.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Company information updated!",
                    "companyId": company.id
                })

            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def ajax_companys(request):
    if request.method == "POST":
        companys = Company.objects.all()

        return render(request, 'sales/company/ajax-company.html', {'companys': companys})

@ajax_login_required
def ajax_companys_filter(request):
    if request.method == "POST":
        company = request.POST.get('company')
        search_country = request.POST.get('search_country')
        associate_filter = request.POST.get('associate_filter')
        if company != "" and search_country == "" and associate_filter == "":
            companys = Company.objects.filter(name__iexact=company)

        elif company != "" and search_country != "" and associate_filter == "":
            companys = Company.objects.filter(name__iexact=company, country_id=search_country)
        
        elif company != "" and search_country != "" and associate_filter != "":
            companys = Company.objects.filter(name__iexact=company, country_id=search_country, associate__iexact=associate_filter)

        elif company == "" and search_country != "" and associate_filter == "":
            companys = Company.objects.filter(country_id=search_country)

        elif company == "" and search_country != "" and associate_filter != "":
            companys = Company.objects.filter(country_id=search_country, associate__iexact=associate_filter)

        elif company == "" and search_country == "" and associate_filter != "":
            companys = Company.objects.filter(associate__iexact=associate_filter)

        elif company != "" and search_country == "" and associate_filter != "":
            companys = Company.objects.filter(name__iexact=company,associate__iexact=associate_filter)

        return render(request, 'sales/company/ajax-company.html', {'companys': companys})

@ajax_login_required
def getCompany(request):
    if request.method == "POST":
        comid = request.POST.get('comid')
        company = Company.objects.get(id=comid)
        data = {
            'name': company.name,
            'address': company.address,
            'unit': company.unit,
            'postalcode': company.postal_code,
            'country': company.country_id,
            'associate': company.associate,

        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def companydelete(request):
    if request.method == "POST":
        com_id = request.POST.get('com_id')
        company = Company.objects.get(id=com_id)
        company.delete()

        return JsonResponse({'status': 'ok'})


@method_decorator(login_required, name='dispatch')
class ContactList(ListView):
    model = Contact
    template_name = "sales/contact/contact-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companys'] = Company.objects.all()
        context['emails'] = Contact.objects.order_by('email').values('email').distinct()
        context['roles'] = Contact.objects.order_by('role').values('role').distinct()
        context['countrys'] = Country.objects.all()
        context['contact_persons'] = Contact.objects.order_by('contact_person').values('contact_person').distinct()
        return context

@ajax_login_required
def contactadd(request):
    if request.method == "POST":
        contactperson = request.POST.get('contactperson')
        salutation = request.POST.get('salutation')
        
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        email = request.POST.get('email')
        role = request.POST.get('role')
        company = request.POST.get('company')
        conid = request.POST.get('conid')
        if conid == "-1":
            try:
                Contact.objects.create(
                    contact_person=contactperson,
                    salutation=salutation,
                    tel=tel,
                    fax=fax,
                    email=email,
                    role=role,
                    company_id=company
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Contact information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already this Contact is existed!"
                })
        else:
            try:
                contact = Contact.objects.get(id=conid)
                contact.contact_person = contactperson
                contact.salutation=salutation
                contact.tel = tel
                contact.fax = fax
                contact.email = email
                contact.role = role
                contact.company_id = company
                contact.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Contact information updated!"
                })

            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def ajax_contacts(request):
    if request.method == "POST":
        contacts = Contact.objects.all()

        return render(request, 'sales/contact/ajax-contact.html', {'contacts': contacts})

@ajax_login_required
def ajax_contacts_filter(request):
    if request.method == "POST":
        contact_person = request.POST.get('contact_person')
        search_email = request.POST.get('search_email')
        role_filter = request.POST.get('role_filter')
        if contact_person != "" and search_email == "" and role_filter == "":
            contacts = Contact.objects.filter(contact_person__iexact=contact_person)

        elif contact_person != "" and search_email != "" and role_filter == "":
            contacts = Contact.objects.filter(contact_person__iexact=contact_person, email=search_email)
        
        elif contact_person != "" and search_email != "" and role_filter != "":
            contacts = Contact.objects.filter(contact_person__iexact=contact_person, email=search_email, role__iexact=role_filter)

        elif contact_person == "" and search_email != "" and role_filter == "":
            contacts = Contact.objects.filter(email=search_email)

        elif contact_person == "" and search_email != "" and role_filter != "":
            contacts = Contact.objects.filter(email=search_email, role__iexact=role_filter)

        elif contact_person == "" and search_email == "" and role_filter != "":
            contacts = Contact.objects.filter(role__iexact=role_filter)

        elif contact_person != "" and search_email == "" and role_filter != "":
            contacts = Contact.objects.filter(contact_person__iexact=contact_person,role__iexact=role_filter)

        return render(request, 'sales/contact/ajax-contact.html', {'contacts': contacts})

@ajax_login_required
def getContact(request):
    if request.method == "POST":
        conid = request.POST.get('conid')
        contact = Contact.objects.get(id=conid)
        data = {
            'contact_person': str(contact.contact_person),
            'salutation': contact.salutation,
            'tel': contact.tel,
            'fax': contact.fax,
            'email': contact.email,
            'company': contact.company_id,
            'role': contact.role,

        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def contactdelete(request):
    if request.method == "POST":
        con_id = request.POST.get('con_id')
        contact = Contact.objects.get(id=con_id)
        contact.delete()

        return JsonResponse({'status': 'ok'})

@method_decorator(login_required, name='dispatch')
class QuotationList(ListView):
    model = Quotation
    template_name = "sales/quotation/quotation-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contacts'] = Contact.objects.all()
        context['companys'] = Company.objects.all()
        context['countrys'] = Country.objects.all()
        context['roles'] = Role.objects.all()
        context['qqtt_ids'] = Quotation.objects.order_by('qtt_id').values('qtt_id').distinct()
        current_year = datetime.datetime.today().year
        if current_year in list(set([d.date.year for d in Quotation.objects.all()])):
            context['exist_current_year'] = True
        else:
            context['exist_current_year'] = False
        context['date_years'] = list(set([d.date.year for d in Quotation.objects.all()]))
        context['customers'] = Quotation.objects.exclude(company_name=None).order_by('company_name').values('company_name').distinct()
        
        return context

@ajax_login_required
def check_quotation_number(request):
    if request.method == "POST":
        if Quotation.objects.all().exists():
            quotation= Quotation.objects.all().order_by('-qtt_id')[0]
            data = {
                "status": "exist",
                "quotation": quotation.qtt_id
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def ajax_quotations(request):
    if request.method == "POST":
        current_year = datetime.datetime.today().year
        quotations = Quotation.objects.filter(date__iso_year=current_year)
        return render(request, 'sales/quotation/ajax-quotation.html', {'quotations': quotations})

@ajax_login_required
def ajax_quotations_filter(request):
    if request.method == "POST":
        search_quotation = request.POST.get('search_quotation')
        daterange = request.POST.get('daterange')
        if daterange:
            startdate = datetime.datetime.strptime(daterange.split()[0],'%Y.%m.%d').replace(tzinfo=pytz.utc)
            enddate = datetime.datetime.strptime(daterange.split()[2], '%Y.%m.%d').replace(tzinfo=pytz.utc)
        search_customer = request.POST.get('search_customer')
        search_year = request.POST.get('search_year')
        if search_year:
            if search_quotation != "" and daterange == "" and search_customer == "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation,date__iso_year=search_year)

            elif search_quotation != "" and daterange != "" and search_customer == "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate,date__iso_year=search_year)
            
            elif search_quotation != "" and daterange != "" and search_customer != "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate, company_name__iexact=search_customer,date__iso_year=search_year)

            elif search_quotation == "" and daterange != "" and search_customer == "":
                quotations = Quotation.objects.filter(date__gte=startdate, date__lte=enddate,date__iso_year=search_year)

            elif search_quotation == "" and daterange != "" and search_customer != "":
                quotations = Quotation.objects.filter(date__gte=startdate, date__lte=enddate, company_name__iexact=search_customer,date__iso_year=search_year)

            elif search_quotation == "" and daterange == "" and search_customer != "":
                quotations = Quotation.objects.filter(company_name__iexact=search_customer)

            elif search_quotation != "" and daterange == "" and search_customer != "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation,company_name__iexact=search_customer,date__iso_year=search_year)

            elif search_quotation == "" and daterange == "" and search_customer == "":
                quotations = Quotation.objects.filter(date__iso_year=search_year)

        else:

            if search_quotation != "" and daterange == "" and search_customer == "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation)

            elif search_quotation != "" and daterange != "" and search_customer == "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate)
            
            elif search_quotation != "" and daterange != "" and search_customer != "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate, company_name__iexact=search_customer)

            elif search_quotation == "" and daterange != "" and search_customer == "":
                quotations = Quotation.objects.filter(date__gte=startdate, date__lte=enddate)

            elif search_quotation == "" and daterange != "" and search_customer != "":
                quotations = Quotation.objects.filter(date__gte=startdate, date__lte=enddate, company_name__iexact=search_customer)

            elif search_quotation == "" and daterange == "" and search_customer != "":
                quotations = Quotation.objects.filter(company_name__iexact=search_customer)

            elif search_quotation != "" and daterange == "" and search_customer != "":
                quotations = Quotation.objects.filter(qtt_id__iexact=search_quotation,company_name__iexact=search_customer)
            
            elif search_quotation == "" and daterange == "" and search_customer == "":
                quotations = Quotation.objects.all()

        return render(request, 'sales/quotation/ajax-quotation.html', {'quotations': quotations})

@ajax_login_required
def check_quotation_company(request):
    if request.method == "POST":
        company = request.POST.get('company')
        if Company.objects.filter(id=company).exists():
            company_info= Company.objects.get(id=company)
            data = {
                "address": company_info.address,
                "unit": company_info.unit,
                "postalcode": company_info.postal_code,
                #"contact_person": company_info.contact_person,
                "country": company_info.country.name,

            }
        
            return JsonResponse(data)

@ajax_login_required
def check_quotation_contact(request):
    if request.method == "POST":
        contact = request.POST.get('contact')
        if Contact.objects.filter(id=contact).exists():
            contact_info= Contact.objects.get(id=contact)
            data = {
                "tel": contact_info.tel,
                "fax": contact_info.fax,
                "email": contact_info.email
            }
        
            return JsonResponse(data)

        else:
            return JsonResponse({})

@ajax_login_required
def quotationadd(request):
    if request.method == "POST":
        qtt_id = request.POST.get('quotationno')
        address = request.POST.get('address')
        subject = request.POST.get('subject')
        contactperson = request.POST.get('contactperson')
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        email = request.POST.get('email')
        company_name = request.POST.get('company')
        quotid = request.POST.get('quotid')
        today = date.today()
        if quotid == "-1":
            try:
                quotation = Quotation.objects.create(
                    qtt_id=qtt_id,
                    address=address,
                    RE=subject,
                    contact_person_id=contactperson,
                    tel=tel,
                    fax=fax,
                    date=today,
                    email=email,
                    company_name_id=company_name,
                    flag=True
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Quotation information added!",
                    "quotationid": quotation.id,
                    "method": "add"
                })
            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Quotation Error!"
                })
        else:
            try:
                quotation = Quotation.objects.get(id=quotid)
                quotation.qtt_id = qtt_id
                quotation.address = address
                quotation.contact_person_id = contactperson
                quotation.tel = tel
                quotation.fax = fax
                quotation.email = email
                quotation.company_name_id = company_name
                quotation.RE = subject
                quotation.date = today
                quotation.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Quotation information updated!",
                    "quotationid": quotation.id,
                    "method": "update"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Quotation Error!"
                })

@ajax_login_required
def getQuotation(request):
    if request.method == "POST":
        quotid = request.POST.get('quotid')
        quotation = Quotation.objects.get(id=quotid)
        data = {
            'qtt_id': quotation.qtt_id,
            'address': quotation.address,
            'subject': quotation.note,
            'company_name': quotation.company_name.name,
            'contactperson': quotation.contact_person_id,
            'tel': quotation.tel,
            'fax': quotation.fax,
            'email': quotation.email,

        }
        return JsonResponse(json.dumps(data), safe=False)


@ajax_login_required
def quotationdelete(request):
    if request.method == "POST":
        quot_id = request.POST.get('quot_id')
        quotation = Quotation.objects.get(id=quot_id)
        quotation.delete()
        if Project.objects.filter(qtt_id__iexact=quotation.qtt_id).exists():
            project = Project.objects.get(qtt_id__iexact=quotation.qtt_id)
            project.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def readnotify(request):
    if request.method == "POST":
        notifyid = request.POST.get('notifyid')
        request.user.notifications.get(id=notifyid).mark_as_read()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def markUserNotificationsRead(request):
    if request.method == 'POST':
        user_id = request.POST['user_id']
        user = User.objects.get(pk=user_id)
        user.notifications.mark_all_as_read()

        return JsonResponse({'status': 'ok'})

@method_decorator(login_required, name='dispatch')
class QuotationDetailView(DetailView):
    model = Quotation
    template_name="sales/quotation/quotation-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        context['quotation'] = Quotation.objects.get(id=content_pk)
        context['quote'] = content_pk
        context['contacts'] = Contact.objects.all()
        context['companies'] = Company.objects.all()
        context['uoms'] = Uom.objects.all()
        data = []
        p_id = [p.id for p in Privilege.objects.all()]
        managers = User.objects.filter(role="Managers").exclude(id__in=p_id)
        if managers:
            data.append(managers)
        data.extend(User.objects.select_related('privilege'))
        context['salepersons'] = data
        context['scope_list'] = Scope.objects.filter(quotation_id=content_pk, parent=None)
        if Scope.objects.filter(quotation_id=content_pk, parent=None).exists():
            subtotal = Scope.objects.filter(quotation_id=content_pk, parent=None).aggregate(Sum('amount'))['amount__sum']
            gst = float(subtotal) * 0.07
            context['subtotal'] = subtotal
            context['gst'] = gst
            context['total_detail'] = float(subtotal) + gst

        if Signature.objects.filter(quotation_id=content_pk).exists():
            context['signaturedata'] = Signature.objects.get(quotation_id=content_pk)
        else:
            context['signaturedata'] = []

        context['file_list'] = QFile.objects.filter(quotation_id=content_pk)
        hot_settings = {
            # 'columnSorting': 'true',
            'contextMenu': 'true',
            'autoWrapRow': 'true',
            'rowHeaders': 'true',
            'contextMenu': 'true',
            'search': 'true',
            'licenseKey': 'non-commercial-and-evaluation',
        }
        context['hot_settings'] = hot_settings
        
        return context

@ajax_login_required
def qfileadd(request):
    if request.method == "POST":
        fname = request.POST.get('fname')
        fileid = request.POST.get('fileid')
        quotationid = request.POST.get('quotationid')
        
        if fileid == "-1":
            try:
                if request.FILES.get('document'):
                    QFile.objects.create(
                        name=fname,
                        user_id=request.user.id,
                        quotation_id=quotationid,
                        document=request.FILES.get('document')
                    )
                else:
                    QFile.objects.create(
                        name=fname,
                        user_id=request.user.id,
                        quotation_id=quotationid
                    )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Quotation File information added!"
                })
            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Quotation File Error!"
                })
        else:
            try:
                qfile = QFile.objects.get(id=fileid)
                qfile.name = fname
                if request.FILES.get('document'):
                    qfile.document = request.FILES.get('document')
                
                qfile.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Quotation File information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Quotation File Error!"
                })

@ajax_login_required
def signaturesave(request):
    if request.method == "POST":
        sname = request.POST.get('sname')
        sdate = request.POST.get('sdate')
        quotationid = request.POST.get('quotationid')
        if Signature.objects.filter(quotation_id=quotationid).exists():
            try:
                signature = Signature.objects.get(quotation_id=quotationid)
                signature.signanture_name=sname
                signature.signature_date = sdate
                

                if request.FILES.get('companycamp') is not None:
                    signature.company_stamp = request.FILES.get('companycamp')
                else:
                    signature.company_stamp = ""

                c_user = User.objects.get(id=request.user.id)
                if request.FILES.get('signature') is not None:
                    c_user.signature = request.FILES.get('signature')
                    c_user.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Signature information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                obj = Signature(
                    signanture_name=sname,
                    signature_date=sdate,
                    quotation_id=quotationid,
                    company_stamp=request.FILES.get('companycamp')
                )
                obj.save()
                c_user = User.objects.get(id=request.user.id)
                if request.FILES.get('signature') is not None:
                    c_user.signature = request.FILES.get('signature')
                    c_user.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Material Inventory information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def scopeadd(request):
    if request.method == "POST":
        sn = request.POST.get('sn')
        qty = request.POST.get('qty')
        uom = request.POST.get('uom')
        description = request.POST.get('description')
        unitprice = request.POST.get('unitprice')
        quotationid = request.POST.get('quotationid')
        scopeid = request.POST.get('scopeid')
        qtt_id = request.POST.get('qtt_id')
        if qty == "" and unitprice == "":
            qty = 0
            unitprice = 0
        
        if scopeid == "-1":
            try:
                Scope.objects.create(
                    sn=sn,
                    qty=qty,
                    uom_id=uom,
                    description=description,
                    amount=Decimal(float(qty)*float(unitprice)),
                    unitprice=Decimal(unitprice),
                    quotation_id=quotationid,
                    qtt_id=qtt_id
                )
                if Scope.objects.filter(quotation_id=quotationid).exists():
                    subtotal = Scope.objects.filter(quotation_id=quotationid).aggregate(Sum('amount'))['amount__sum']
                    gst = float(subtotal) * 0.07
                    total_detail = float(subtotal) + gst
                    quotation = Quotation.objects.get(id=quotationid)
                    quotation.total = Decimal(total_detail)
                    quotation.save()
                    if Scope.objects.filter(Q(quotation_id=quotationid), ~Q(qtt_id=None)).exists():
                        scope_temp = Scope.objects.filter(Q(quotation_id=quotationid), ~Q(qtt_id=None))[0]
                        if SaleReport.objects.filter(qtt_id__iexact=scope_temp.qtt_id).exists():
                            salereport = SaleReport.objects.get(qtt_id__iexact=scope_temp.qtt_id)
                            salereport.finaltotal = Decimal(total_detail)
                            salereport.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "Contact information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already this Contact is existed!"
                })
        else:
            
            try:
                scope = Scope.objects.get(id=scopeid)
                scope.sn = sn
                scope.qty = qty
                scope.uom_id = uom
                scope.description = description
                scope.amount = Decimal(float(qty) * float(unitprice))
                scope.unitprice = Decimal(unitprice)
                scope.quotation_id = quotationid
                scope.qtt_id = qtt_id
                scope.save()
                
                if Scope.objects.filter(quotation_id=quotationid).exists():
                    subtotal = Scope.objects.filter(quotation_id=quotationid).aggregate(Sum('amount'))['amount__sum']
                    gst = float(subtotal) * 0.07
                    total_detail = float(subtotal) + gst
                    quotation = Quotation.objects.get(id=quotationid)
                    quotation.total = Decimal(total_detail)
                    quotation.save()
                    if Scope.objects.filter(Q(quotation_id=quotationid), ~Q(qtt_id=None)).exists():
                        scope_temp = Scope.objects.filter(Q(quotation_id=quotationid), ~Q(qtt_id=None))[0]
                        if SaleReport.objects.filter(qtt_id__iexact=scope_temp.qtt_id).exists():
                            salereport = SaleReport.objects.get(qtt_id__iexact=scope_temp.qtt_id)
                            salereport.finaltotal = Decimal(total_detail)
                            salereport.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Scope information updated!"
                })

            except IntegrityError as e: 
                print(e)
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

class DecimalEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      return str(obj)
    return json.JSONEncoder.default(self, obj)

@ajax_login_required
def ajax_filter_person(request):
    if request.method == "POST":
        company = request.POST.get('company')
        contacts = Contact.objects.filter(company_id = company)
        return render(request, 'sales/quotation/ajax-contact.html', {'contacts': contacts})

@ajax_login_required
def getScope(request):
    if request.method == "POST":
        scopeid = request.POST.get('scopeid')
        scope = Scope.objects.get(id=scopeid)
        data = {
            'sn': scope.sn,
            'qty': scope.qty,
            'uom': scope.uom,
            'unitprice': scope.unitprice,
            'description': scope.description,
        }
        return JsonResponse(json.dumps(data, cls=DecimalEncoder), safe=False)
    
@ajax_login_required
def getFile(request):
    if request.method == "POST":
        fileid = request.POST.get('fileid')
        qfile = QFile.objects.get(id=fileid)
        if qfile.document:
            data = {
                'name': qfile.name,
                'document': qfile.document.url,
            }
        else:
            data = {
                'name': qfile.name,
                'document': "",
            }
        return JsonResponse(json.dumps(data, cls=DecimalEncoder), safe=False)

@ajax_login_required
def scopedelete(request):
    if request.method == "POST":
        scopeid = request.POST.get('scopeid')
        scope = Scope.objects.get(id=scopeid)
        scope.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def qfiledelete(request):
    if request.method == "POST":
        fileid = request.POST.get('fileid')
        file = QFile.objects.get(id=fileid)
        file.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def UpdateQuotation(request):
    if request.method == "POST":
        
        company_name = request.POST.get('company_name')
        address = request.POST.get('address')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        note = request.POST.get('note')
        re = request.POST.get('re')
        qtt_id = request.POST.get('qtt_id')
        sale_type = request.POST.get('sale_type')
        date = request.POST.get('date')
        qtt_status = request.POST.get('qtt_status')
        sale_person = request.POST.get('sale_person')
        estimated_mandays = request.POST.get('estimated_mandays')
        po_no = request.POST.get('po_no')
        validity = request.POST.get('validity')
        terms = request.POST.get('terms')
        material_lead_time = request.POST.get('material_lead_time')
        quotid = request.POST.get('quotid')
        
        try:
            quotation = Quotation.objects.get(id=quotid)

            if quotation.qtt_status != qtt_status:
                sender = request.user
                description = 'Quotation No : ' + quotation.qtt_id +  ' - status was changed as ' + qtt_status
                for receiver in User.objects.all():
                    notify.send(sender, recipient=receiver, verb='Message', level="success", description=description)
            
            quotation.company_name_id=company_name
            quotation.address=address
            quotation.contact_person_id=contact_person
            quotation.email=email
            quotation.tel=tel
            quotation.fax=fax
            quotation.qtt_id=qtt_id
            quotation.sale_type=sale_type
            quotation.date=date
            quotation.qtt_status=qtt_status
            quotation.note=note
            quotation.RE=re
            quotation.sale_person=sale_person
            quotation.estimated_mandays=estimated_mandays
            quotation.po_no = po_no
            quotation.material_leadtime = material_lead_time
            quotation.validity = validity
            quotation.terms = terms
            quotation.flag=True
            quotation.save()
            if qtt_status == "Awarded" and sale_type == "Project":
                
                if Project.objects.filter(qtt_id__iexact=qtt_id).exists():
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    
                    proj= Project.objects.all().order_by('-proj_id')[0]
                    if int(proj.proj_id[3:5]) == int(currentyear):
                        proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                    else:
                        proj_id = prefix + str(currentyear) + "1001"

                    project = Project.objects.get(qtt_id__iexact=qtt_id)
                    #project.proj_id=proj_id
                    project.company_name_id=company_name
                    project.tel=tel
                    project.fax=fax
                    project.proj_status="Open"
                    project.start_date=date
                    project.RE=re
                    project.email=email
                    project.qtt_id=qtt_id
                    project.quotation_id=quotid
                    project.estimated_mandays=estimated_mandays
                    project.save()

                else:
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    if Project.objects.all().exists():
                        proj= Project.objects.all().order_by('-proj_id')[0]
                        if int(proj.proj_id[3:5]) == int(currentyear):
                            proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                        else:
                            proj_id = prefix + str(currentyear) + "1001"

                    else:
                        proj_id = prefix + str(currentyear) + "1001"

                    newproject = Project.objects.create(
                        proj_id=proj_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        proj_status="Open",
                        start_date=date,
                        RE=re,
                        email=email,
                        qtt_id=qtt_id,
                        estimated_mandays=estimated_mandays,
                        contact_person_id=contact_person,
                        quotation_id=quotid
                    )
                    #notification send
                    sender = request.user
                    description = 'Project No : ' + newproject.proj_id +  ' - New Project was created by ' + request.user.username
                    for receiver in User.objects.all():
                        if receiver.notificationprivilege.project_no_created:
                            notify.send(sender, recipient=receiver, verb='Message', level="success", description=description)


            elif qtt_status == "Awarded" and sale_type == "Maintenance":
                if Maintenance.objects.filter(quot_no__iexact=qtt_id).exists():
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    main= Maintenance.objects.all().order_by('-main_no')[0]
                    if int(main.main_no[3:5]) == int(currentyear):
                        main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                    else:
                        main_id = prefix + str(currentyear) + "1001"

                    maintenance = Maintenance.objects.get(quot_no__iexact=qtt_id)
                    #maintenance.main_no=main_id
                    maintenance.company_name_id=company_name
                    maintenance.tel=tel
                    maintenance.fax=fax
                    maintenance.main_status="Open"
                    maintenance.start_date=date
                    maintenance.RE=re
                    maintenance.email=email
                    maintenance.quot_no=qtt_id
                    maintenance.contact_person_id=contact_person
                    maintenance.save()
                else:
                    
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    if Maintenance.objects.all().exists():
                        main= Maintenance.objects.all().order_by('-main_no')[0]
                        if int(main.main_no[3:5]) == int(currentyear):
                            main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                        else:
                            main_id = prefix + str(currentyear) + "1001"

                    else:
                        main_id = prefix + str(currentyear) + "1001"
                    Maintenance.objects.create(
                        main_no=main_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        main_status="Open",
                        start_date=date,
                        RE=re,
                        quotation_id=quotid,
                        email=email,
                        quot_no=qtt_id,
                        contact_person_id=contact_person
                    )   

               
            if SaleReport.objects.filter(qtt_id=qtt_id).exists():
                salereport = SaleReport.objects.get(qtt_id__iexact=qtt_id)
                salereport.qtt_id=qtt_id
                salereport.company_name_id=company_name
                salereport.address=address
                salereport.email=email
                salereport.sale_person=sale_person
                salereport.qtt_status=qtt_status
                salereport.sale_type=sale_type
                salereport.date=date
                salereport.RE=re
                salereport.contact_person_id=contact_person
                if Scope.objects.filter(quotation_id=quotation.id).exists():
                    subtotal = Scope.objects.filter(quotation_id=quotation.id).aggregate(Sum('amount'))['amount__sum']
                    gst = float(subtotal) * 0.07
                    total_detail = float(subtotal) + gst
                    salereport.finaltotal = Decimal(total_detail)
                salereport.save()
            else:
                sale = SaleReport(
                    qtt_id=qtt_id,
                    company_name_id=company_name,
                    address=address,
                    email=email,
                    sale_person=sale_person,
                    qtt_status=qtt_status,
                    sale_type=sale_type,
                    date=date,
                    RE=re,
                    quotation_id=quotid,
                    contact_person_id=contact_person
                )
                if Scope.objects.filter(quotation_id=quotation.id).exists():
                    subtotal = Scope.objects.filter(quotation_id=quotation.id).aggregate(Sum('amount'))['amount__sum']
                    gst = float(subtotal) * 0.07
                    total_detail = float(subtotal) + gst
                    sale.finaltotal = Decimal(total_detail)
                sale.save()
            return JsonResponse({
                "status": "Success",
                "messages": "Quotation information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@ajax_login_required
def UpdateQuotationOverride(request):
    if request.method == "POST":
        
        company_name = request.POST.get('company_name')
        address = request.POST.get('address')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        note = request.POST.get('note')
        re = request.POST.get('re')
        qtt_id = request.POST.get('qtt_id')
        sale_type = request.POST.get('sale_type')
        date = request.POST.get('date')
        qtt_status = request.POST.get('qtt_status')
        sale_person = request.POST.get('sale_person')
        po_no = request.POST.get('po_no')
        validity = request.POST.get('validity')
        terms = request.POST.get('terms')
        estimated_mandays = request.POST.get('estimated_mandays')
        material_lead_time = request.POST.get('material_lead_time')
        quotid = request.POST.get('quotid')
        if len(qtt_id.split("-")) == 1:
            new_qtt_id = qtt_id + "-1"
        else:
            new_qtt_id = qtt_id.split("-")[0] + "-" + str(int(qtt_id.split("-")[1]) + 1)
        try:
            quotation = Quotation.objects.get(id=quotid)
            
            # quotation.company_name=company_name
            # quotation.address=address
            # quotation.contact_person=contact_person
            # quotation.email=email
            # quotation.tel=tel
            # quotation.fax=fax
            # quotation.qtt_id=qtt_id
            # quotation.sale_type=sale_type
            # quotation.date=date
            # quotation.qtt_status=qtt_status
            # quotation.note=note
            quotation.flag=False
            # quotation.sale_person=sale_person
            quotation.save()

            new = Quotation(
                company_name_id=company_name,
                address=address,
                contact_person_id=contact_person,
                email=email,
                tel=tel,
                fax=fax,
                qtt_id=new_qtt_id,
                sale_type=sale_type,
                date=date,
                qtt_status=qtt_status,
                note=note,
                RE=re,
                sale_person=sale_person,
                estimated_mandays=estimated_mandays,
                validity = validity,
                terms = terms,
                po_no = po_no,
                material_leadtime = material_lead_time,
                flag=True
                
            )
            new.save()
            if SaleReport.objects.filter(qtt_id=qtt_id).exists():
                # salereport = SaleReport.objects.get(qtt_id__iexact=qtt_id)
                # salereport.qtt_id=qtt_id
                # salereport.company_name=company_name
                # salereport.address=address
                # salereport.email=email
                # salereport.sale_person=sale_person
                # salereport.qtt_status=qtt_status
                # salereport.sale_type=sale_type
                # salereport.date=date
                # salereport.contact_person=contact_person
                # salereport.save()
                print("exist")
            else:
                sale = SaleReport(
                    qtt_id=qtt_id,
                    company_name_id=company_name,
                    address=address,
                    email=email,
                    sale_person=sale_person,
                    qtt_status=qtt_status,
                    sale_type=sale_type,
                    date=date,
                    contact_person_id=contact_person
                )
                sale.save()

            if SaleReport.objects.filter(qtt_id=new.qtt_id).exists():
                salereport = SaleReport.objects.get(qtt_id__iexact=new.qtt_id)
                salereport.qtt_id=new.qtt_id
                salereport.company_name_id=company_name
                salereport.address=address
                salereport.email=email
                salereport.sale_person=sale_person
                salereport.qtt_status=qtt_status
                salereport.sale_type=sale_type
                salereport.date=date
                salereport.contact_person_id=contact_person
                salereport.save()
            else:
                sale = SaleReport(
                    qtt_id=new.qtt_id,
                    company_name_id=company_name,
                    address=address,
                    email=email,
                    sale_person=sale_person,
                    qtt_status=qtt_status,
                    sale_type=sale_type,
                    date=date,
                    contact_person_id=contact_person
                )
                sale.save()
            scopedata = Scope.objects.filter(quotation_id=quotid)
            for scoped in scopedata:
                Scope.objects.create(
                    qty=scoped.qty,
                    uom=scoped.uom,
                    description=scoped.description,
                    amount=Decimal(float(scoped.qty)*float(scoped.unitprice)),
                    unitprice=Decimal(scoped.unitprice),
                    quotation_id=new.id,
                    qtt_id=new_qtt_id
                )
            if scopedata:
                
                subtotal = Scope.objects.filter(quotation_id=new.id).aggregate(Sum('amount'))['amount__sum']
                gst = float(subtotal) * 0.07
                total_detail = float(subtotal) + gst
                quotation = Quotation.objects.get(id=new.id)
                quotation.total = Decimal(total_detail)
                quotation.save()
                
                if SaleReport.objects.filter(qtt_id__iexact=str(quotation.qtt_id)).exists():
                    salereport = SaleReport.objects.get(qtt_id__iexact=str(quotation.qtt_id))
                    salereport.finaltotal = Decimal(total_detail)
                    salereport.save()
                
            if qtt_status == "Awarded" and sale_type == "Project":
                
                if Project.objects.filter(qtt_id__iexact=qtt_id).exists() == False:
                    
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    if Project.objects.all().exists():
                        proj= Project.objects.all().order_by('-proj_id')[0]
                        if int(proj.proj_id[3:5]) == int(currentyear):
                            proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                        else:
                            proj_id = prefix + str(currentyear) + "1001"

                    else:
                        proj_id = prefix + str(currentyear) + "1001"
                    Project.objects.create(
                        proj_id=proj_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        proj_status="Open",
                        start_date=date,
                        RE=re,
                        email=email,
                        estimated_mandays=estimated_mandays,
                        qtt_id=qtt_id,
                        quotation_id=new.id
                    )
                else:
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    
                    proj= Project.objects.all().order_by('-proj_id')[0]
                    if int(proj.proj_id[3:5]) == int(currentyear):
                        proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                    else:
                        proj_id = prefix + str(currentyear) + "1001"
                    project = Project.objects.get(qtt_id__iexact=qtt_id)
                    #project.proj_id=proj_id
                    project.company_name_id=company_name
                    project.tel=tel
                    project.fax=fax
                    project.proj_status="Open"
                    project.start_date=date
                    project.RE=re
                    project.email=email
                    project.qtt_id=qtt_id
                    project.estimated_mandays=estimated_mandays
                    project.quotation_id=new.id
                    project.save()

                if Project.objects.filter(qtt_id__iexact=new.qtt_id).exists() == False:
                    
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    if Project.objects.all().exists():
                        proj= Project.objects.all().order_by('-proj_id')[0]
                        if int(proj.proj_id[3:5]) == int(currentyear):
                            proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                        else:
                            proj_id = prefix + str(currentyear) + "1001"

                    else:
                        proj_id = prefix + str(currentyear) + "1001"

                    Project.objects.create(
                        proj_id=proj_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        proj_status="Open",
                        start_date=date,
                        RE=re,
                        email=email,
                        qtt_id=new.qtt_id
                    )
                else:
                    prefix = "CPJ"
                    currentyear = time.strftime("%y", time.localtime())
                    
                    proj= Project.objects.all().order_by('-proj_id')[0]
                    if int(proj.proj_id[3:5]) == int(currentyear):
                        proj_id = prefix + str(currentyear) + str(int(proj.proj_id[5:]) + 1)
                    else:
                        proj_id = prefix + str(currentyear) + "1001"

                    project = Project.objects.get(qtt_id__iexact=qtt_id)
                    #project.proj_id=proj_id
                    project.company_name_id=company_name
                    project.tel=tel
                    project.fax=fax
                    project.proj_status="Open"
                    project.start_date=date
                    project.RE=re
                    project.email=email
                    project.qtt_id=new.qtt_id
                    project.save()


            elif qtt_status == "Awarded" and sale_type == "Maintenance":
                
                if Maintenance.objects.filter(quot_no__iexact=qtt_id).exists() == False:
                    
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    if Maintenance.objects.all().exists():
                        main= Maintenance.objects.all().order_by('-main_no')[0]
                        if int(main.main_no[3:5]) == int(currentyear):
                            main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                        else:
                            main_id = prefix + str(currentyear) + "1001"

                    else:
                        main_id = prefix + str(currentyear) + "1001"
                    Maintenance.objects.create(
                        main_no=main_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        main_status="Open",
                        start_date=date,
                        RE=re,
                        quotation_id=quotid,
                        email=email,
                        quot_no=qtt_id,
                        contact_person_id=contact_person
                    )
                else:
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    main= Maintenance.objects.all().order_by('-main_no')[0]
                    if int(main.main_no[3:5]) == int(currentyear):
                        main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                    else:
                        main_id = prefix + str(currentyear) + "1001"

                    maintenance = Maintenance.objects.get(quot_no__iexact=qtt_id)
                    #maintenance.main_no=main_id
                    maintenance.company_name_id=company_name
                    maintenance.tel=tel
                    maintenance.fax=fax
                    maintenance.main_status="Open"
                    maintenance.start_date=date
                    maintenance.RE=re
                    maintenance.email=email
                    maintenance.quot_no=qtt_id
                    maintenance.contact_person_id=contact_person
                    maintenance.save()

                if Maintenance.objects.filter(quot_no__iexact=new.qtt_id).exists() == False:
                    
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    if Maintenance.objects.all().exists():
                        main= Maintenance.objects.all().order_by('-main_no')[0]
                        if int(main.main_no[3:5]) == int(currentyear):
                            main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                        else:
                            main_id = prefix + str(currentyear) + "1001"

                    else:
                        main_id = prefix + str(currentyear) + "1001"
                    Maintenance.objects.create(
                        main_no=main_id,
                        company_name_id=company_name,
                        tel=tel,
                        fax=fax,
                        main_status="Open",
                        start_date=date,
                        RE=re,
                        quotation_id=quotid,
                        email=email,
                        quot_no=new.qtt_id
                    )
                else:
                    prefix = "CMT"
                    currentyear = time.strftime("%y", time.localtime())
                    main= Maintenance.objects.all().order_by('-main_no')[0]
                    if int(main.main_no[3:5]) == int(currentyear):
                        main_id = prefix + str(currentyear) + str(int(main.main_no[5:]) + 1)
                    else:
                        main_id = prefix + str(currentyear) + "1001"

                    maintenance = Maintenance.objects.get(quot_no__iexact=qtt_id)
                    #maintenance.main_no=main_id
                    maintenance.company_name_id=company_name
                    maintenance.tel=tel
                    maintenance.fax=fax
                    maintenance.main_status="Open"
                    maintenance.start_date=date
                    maintenance.RE=re
                    maintenance.email=email
                    maintenance.quot_no=new.qtt_id
                    maintenance.save()

            
            return JsonResponse({
                "status": "Success",
                "messages": "Quotation information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

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

def exportQuotationPDF(request, value):
    
    quotation = Quotation.objects.get(id=value)
    quotationitems = Scope.objects.filter(quotation_id=value)
    domain = request.META['HTTP_HOST']
    logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    response = HttpResponse(content_type='application/pdf')
    currentdate = date.today()
    pdfname = quotation.qtt_id + ".pdf"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(pdfname)
    
    story = []
    data= [
        [Paragraph('''<para align=left><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=left><font size=10><b>Description</b></font></para>'''), Paragraph('''<para align=left><font size=10><b>UOM</b></font></para>'''), Paragraph('''<para align=left><font size=10><b>QTY</b></font></para>'''), Paragraph('''<para align=left><font size=10><b>U/Price(S$)</b></font></para>'''), Paragraph('''<para align=left><font size=10><b>Amount(S$)</b></font></para>''')],
    ]
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=portrait(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.25*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    style_head = ParagraphStyle("justifies", leading=16)
    
    
    quoinformation = []
    if quotation.material_leadtime:
        qmaterial_leadtime =  quotation.material_leadtime
    else:
        qmaterial_leadtime = " "
    if quotation.validity:
        qvalidity =  quotation.validity
    else:
        qvalidity = " "
    if quotation.terms:
        qterms =  quotation.terms
    else:
        qterms = " "
    if quotation.date:
        qdate =  quotation.date.strftime('%d/%m/%Y')
    else:
        qdate = " "
    if quotation.sale_person:
        qsaleperson =  quotation.sale_person
    else:
        qsaleperson = " "
    quotation_title = '''
        <para align=left>
            <font size=16><b>QUOTATION</b></font><br/>
            <font size=10>Quotation No: %s</font><br/>
            <font size=10>Date: %s</font><br/>
            <font size=10>Prepared By: %s</font>
        </para>
    ''' % (quotation.qtt_id, qdate, qsaleperson)
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
    quo_to = '''
        <para align=left>
            <font size=10>%s</font><br/>
            <font size=10>%s</font><br/>
            
        </para> 
    ''' % (quotation.company_name.name, str(quotation.address))
    quotation_to = '''
        <para align=left>
            <font size=10>To: </font>
        </para>
    '''
    quo_head = ParagraphStyle("justifies", leading=18)
    quoinformation.append([Paragraph(quotation_to), Paragraph(quo_to, quo_head), "", Paragraph(quotation_title, quo_head)])
    information = Table(
        quoinformation,
        style=[
            ('ALIGN',(-1,0),(-1,0),'LEFT'),
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(0,0),'TOP'),
            ('VALIGN',(-1,0),(-1,0),'TOP'),
            ('VALIGN',(1,0),(1,0),'TOP'),
        ]
    )
    
    information._argW[0]=0.5*inch
    information._argW[1]=3.0*inch
    information._argW[2]=2.4*inch
    information._argW[3]=1.6*inch
    story.append(Spacer(1, 16))
    story.append(information)
    infordetail = []
    quotation_attn = '''
        <para align=left>
            <font size=10>Attn:  %s</font>
        </para>
    ''' % (quotation.contact_person.salutation + " " + quotation.contact_person.contact_person)
    quotation_email = '''
        <para align=left>
            <font size=10>Email:  %s</font>
        </para>
    ''' % (quotation.email)
    quotation_tel = '''
        <para align=left>
            <font size=10>Tel:  %s</font>
        </para>
    ''' % (quotation.tel)
    quotation_fax = '''
        <para align=left>
            <font size=10>Fax:  %s</font>
        </para>
    ''' % (quotation.fax)
    quotation_re = '''
        <para align=left>
            <font size=10>RE:   %s</font>
        </para>
    ''' % (quotation.RE)
    infordetail.append([Paragraph(quotation_attn), Paragraph(quotation_email), ""])
    infordetail.append([Paragraph(quotation_tel), Paragraph(quotation_fax), ""])
    infor = Table(
        infordetail,
        style=[
            ('VALIGN',(0,0),(-1,1), "TOP"),
        ],
    )
    
    infor._argW[0]=2.0*inch
    infor._argW[1]=2.5*inch
    infor._argW[2]=3.0*inch
    infor._argH[0]=0.32*inch
    infor._argH[1]=0.32*inch
    story.append(infor)
    style_re = ParagraphStyle(name='left',fontSize=16, parent=styleSheet['Normal'], leftIndent=10)
    story.append(Spacer(1, 10))
    story.append(Paragraph(quotation_re,style_re))
    index = 1
    for quotationitem in quotationitems:
        temp_data = []
        description = '''
            <para align=left>
                %s
            </para>
        ''' % (str(quotationitem.description))
        pdes = Paragraph(description, styleSheet["BodyText"])
        temp_data.append(str(index))
        temp_data.append(pdes)
        temp_data.append(str(quotationitem.uom))
        temp_data.append(str(quotationitem.qty))
        temp_data.append(str(quotationitem.unitprice))
        temp_data.append(str(quotationitem.amount))
        data.append(temp_data)
        index += 1
    note = []
    note.append("")
    
    if quotation.note:
        note_content = quotation.note 
    else:
        note_content = ""
    note.append(Paragraph('''<para align=left><font size=9><u><b><i>NOTE: </i></b></u><br/>%s</font></para>''' % note_content))
    
    if Scope.objects.filter(quotation_id=value, parent=None).exists():
        data.append(note)
        statistic = []
        subtotal = Scope.objects.filter(quotation_id=value, parent=None).aggregate(Sum('amount'))['amount__sum']
        gst = float(subtotal) * 0.07
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")

        statistic.append(Paragraph('''<para align=left><font size=9><b>TOTAL</b></font></para>'''))
        statistic.append("$ " + '%.2f' % float(subtotal))
        data.append(statistic)
        statistic = []
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append(Paragraph('''<para align=left><font size=9><b>ADD GST 7%</b></font></para>'''))
        statistic.append("$ " + '%.2f' % float(gst))
        data.append(statistic)
        statistic = []
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append("")
        statistic.append(Paragraph('''<para align=left><font size=9><b>FINAL TOTAL</b></font></para>'''))
        statistic.append("$ " + '%.2f' % (float(subtotal) + gst))
        data.append(statistic)

        exportD=Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (5, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('SPAN',(1,-5),(-1,-5)),
                ('SPAN',(1,-4),(-1,-4)),
                ('VALIGN',(1,-4),(-1,-4), "MIDDLE"),
            ],
        )
    else:
        data.append(["No data available in table", "", "", "", "", "",])
        data.append(note)
        exportD=Table(
            data,
            style=[
                ('BACKGROUND', (0, 0), (5, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('SPAN',(1,2),(-1,2)),
                ('VALIGN',(0,0),(-1,-1), "MIDDLE"),
                ('ALIGN',(1,2),(-1,2), "CENTER"),
                ('SPAN',(0,1),(-1,1)),
                ('ALIGN',(0,1),(-1,1), "CENTER"),
                ('SPAN',(1,3),(-1,3)),
                ('ALIGN',(1,3),(-1,3), "CENTER"),
            ],
        )
    exportD._argW[0]=0.40*inch
    exportD._argW[1]=3.59*inch
    exportD._argW[2]=0.732*inch
    exportD._argW[3]=0.732*inch
    exportD._argW[4]=1.0*inch
    exportD._argW[5]=1.0*inch
    story.append(Spacer(1, 15))
    story.append(exportD)
    story.append(Spacer(1, 15))
    style_term = ParagraphStyle(name='right',fontSize=14, parent=styleSheet['Normal'], leftIndent=10)
    
    story.append(Paragraph('''<para align=left><font><u><i><b>Terms & Conditions</b></i></u></font></para>''', style_term))
    story.append(Spacer(1, 15))
    style_condition = ParagraphStyle(name='right',fontSize=9, parent=styleSheet['Normal'], leftIndent=20, leading=15)
    story.append(Paragraph('''<para align=left><font>● Validity : %s days </font></para>''' % (qvalidity), style_condition))
    story.append(Paragraph('''<para align=left><font>● Payment : %s </font></para>''' % (qterms), style_condition))
    story.append(Paragraph('''<para align=left><font>● Material Leadtime : %s </font></para>''' % (qmaterial_leadtime), style_condition))
    story.append(Paragraph("● Note : Price quoted for normal working hours unless stated", style_condition))
    story.append(Paragraph("● Note : CNI Technology Pte Ltd reserve the right to revise the prices should the quantity ordered and/or called up differ from the above.", style_condition))
    story.append(Paragraph("● Note : Additional Services & Material not listed in the above quotation will be considered variation order and will be quoted separately upon request.", style_condition))
    story.append(Paragraph("● Note : Please be informed that unless payment is received in full, CNI Technology Pte Ltd will remain as the rightful owner of the delivered equipment(s)/material(s) on site.", style_condition))
    story.append(Paragraph("● Note : All cancellation of order after receiving of Purchase Order or Confirmation will be subjected to 40% charge of the contract sum.", style_condition))
    story.append(Spacer(1, 10))
    style_sign_des = ParagraphStyle(name='right',fontSize=10, parent=styleSheet['Normal'])
    quotation_signname = '''
        <para align=left>
            <font size=10><b>Authorised Name:</b>  %s</font>
        </para>
    ''' % (request.user.username)
    currentdate = date.today().strftime("%d-%m-%Y")
    quotation_date = '''
        <para align=left>
            <font size=10><b>Date:</b>  %s</font>
        </para>
    ''' % (currentdate)
    style_sign = ParagraphStyle(name='right',fontSize=10, parent=styleSheet['Normal'])
    sign_title = '''
        <para align=left>
            <font size=10><b>Authorised  Signature: </b></font>
        </para>
    '''
    if request.user.signature:
        sign_logo = Image('http://' + domain + request.user.signature.url, width=0.8*inch, height=0.8*inch, hAlign='LEFT')
    else:
        sign_logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    approvalD=Table(
        [
            [Paragraph('''<para align=left><font size=13><i><b>Customer's Approval</b></i></font></para>''')],
            [Paragraph("We confirm and accept your above quotation. Kindly proceed with our order.", style_sign_des)],
            # [Paragraph(quotation_signname, style_sign),"", Paragraph(quotation_date, style_sign)],
            # [Paragraph(sign_title, style_sign), sign_logo]
            [Paragraph('''<para align=left><font size=10><b>Authorised Name:</b></font></para>''', style_sign),"", Paragraph('''<para align=left><font size=10><b>Date:</b></font></para>''', style_sign)],
            [Paragraph('''<para align=left><font size=10><b>Authorised  Signature:</b></font></para>''', style_sign),"", Paragraph("", style_sign)],
            ["","", ""],
            ["","", ""],
            ["","", ""],
        ],
        style=[
            ('BACKGROUND', (0, 0), (0, 0), colors.lavender),
            ('BOX',(0,0),(2,-1),0.5,colors.black),
            ('SPAN',(0,0),(2,0)),
            ('SPAN',(0,1),(2,1)),
            ('VALIGN',(0,-1),(0,-1),'TOP'),
            ('VALIGN',(0,0),(0,0),'TOP'),
            ('LINEABOVE',(0,1),(2,1),0.5,colors.black),
            ('SPAN',(1,1),(-1,1)),
        ],
    )
    approvalD._argW[0]=1.8*inch
    approvalD._argW[1]=1.8*inch
    approvalD._argW[2]=3.72*inch
    approvalD._argH[0]=0.32*inch
    approvalD._argH[1]=0.32*inch
    approvalD._argH[2]=0.32*inch
    # if quotationitems.exists():      
    #     story.append(PageBreak())
    #     story.append(Spacer(1, 16))

    story.append(approvalD)
    doc.build(story,canvasmaker=NumberedCanvas)
    
    response.write(buff.getvalue())
    buff.close()
    return response


def exportExcelQuotation(request, value):
    response = HttpResponse(content_type='application/ms-excel')
    currentdate = date.today()
    excelname = "ERP-SOLUTION-Quotation-" + currentdate.strftime("%d-%m-%Y") + ".xls"
    response['Content-Disposition'] = 'attachment; filename={}'.format(excelname)
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Quotation')
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    columns = ['Quotation No', 'Company name','Contact Person', 'Email',  'Tel', 'Fax', 'RE', 'Sale Type','Sale Person','Date','Status']
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    rows = Quotation.objects.filter(id=value).values_list('qtt_id', 'company_name', 'contact_person', 'email', 'tel', 'fax','note', 'sale_type', 'sale_person', 'date', 'qtt_status')
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            if isinstance(row[col_num], datetime.date) == True:
                temp = list(row)
                temp[col_num] = temp[col_num].strftime('%d %b, %Y')
                row = tuple(temp)
            ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response


@method_decorator(login_required, name='dispatch')
@method_decorator(sale_report_privilege_required, name='dispatch')
class ReportView(ListView):
    model = SaleReport
    template_name = "sales/report/report-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companys'] =  Company.objects.all()
        if self.request.user.role == "Managers" or self.request.user.is_staff == True:
            context['sqtt_ids'] = SaleReport.objects.order_by('qtt_id').values('qtt_id').distinct()
            context['salepersons'] = SaleReport.objects.exclude(sale_person=None).order_by('sale_person').values('sale_person').distinct()
        else:
            context['sqtt_ids'] = SaleReport.objects.filter(sale_person__iexact=self.request.user.username).order_by('qtt_id').values('qtt_id').distinct()
            context['salepersons'] = SaleReport.objects.exclude(sale_person=None).filter(sale_person__iexact=self.request.user.username).order_by('sale_person').values('sale_person').distinct()
        return context

@ajax_login_required
def salereportadd(request):
    if request.method == "POST":
        qtt_id = request.POST.get('qtt_id')
        date = request.POST.get('date')
        address = request.POST.get('address')
        company_name = request.POST.get('company_name')
        sale_person = request.POST.get('sale_person')
        qtt_status = request.POST.get('qtt_status')
        reportid = request.POST.get('reportid')
        if reportid == "-1":
            try:
                SaleReport.objects.create(
                    qtt_id=qtt_id,
                    date=date,
                    company_name=company_name,
                    address=address,
                    sale_person=sale_person,
                    qtt_status=qtt_status,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Report information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                report = SaleReport.objects.get(id=reportid)
                report.qtt_id = qtt_id
                report.date = date
                report.address = address
                report.company_name = company_name
                report.sale_person = sale_person
                report.qtt_status = qtt_status
               
                report.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Report information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })


@ajax_login_required
def getReport(request):
    if request.method == "POST":
        reportid = request.POST.get('reportid')
        salereport = SaleReport.objects.get(id=reportid)
        data = {
            'qtt_id': salereport.qtt_id,
            'address': salereport.address,
            'date': salereport.date.strftime('%d %b, %Y'),
            'company_name': salereport.company_name,
            'sale_person': salereport.sale_person,
            'qtt_status': salereport.qtt_status,

        }
        return JsonResponse(json.dumps(data), safe=False)


@ajax_login_required
def reportdelete(request):
    if request.method == "POST":
        reportid = request.POST.get('reportid')
        company = SaleReport.objects.get(id=reportid)
        company.delete()

        return JsonResponse({'status': 'ok'})

@method_decorator(login_required, name='dispatch')
class ReportDetailView(DetailView):
    model = SaleReport
    template_name="sales/report/report-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        context['salereport'] = SaleReport.objects.get(id=content_pk)
        context['salerep'] = content_pk
        context['contacts'] = Contact.objects.all()
        context['comments'] = SaleReportComment.objects.filter(salereport_id=content_pk)
        return context

@ajax_login_required
def UpdateReport(request):
    if request.method == "POST":
        
        company_name = request.POST.get('company_name')
        address = request.POST.get('address')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        amount = request.POST.get('amount')
        sale_person = request.POST.get('sale_person')
        note = request.POST.get('note')
        qtt_id = request.POST.get('qtt_id')
        sale_type = request.POST.get('sale_type')
        date = request.POST.get('date')
        qtt_status = request.POST.get('qtt_status')
        reportid = request.POST.get('reportid')
        try:
            report = SaleReport.objects.get(id=reportid)
            
            report.company_name=company_name
            report.address=address
            report.contact_person_id=contact_person
            report.email=email
            report.sale_person=sale_person
            report.finaltotal=amount
            report.qtt_id=qtt_id
            report.sale_type=sale_type
            report.date=date
            report.qtt_status=qtt_status
            report.RE=note
            report.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Report information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@ajax_login_required
def addSaleComment(request):
    if request.method == "POST":

        today = date.today()
        comment = request.POST['comment']
        salereportid= request.POST['salereportid']
        commentid = request.POST['commentid']
        if request.user.username:
            comment_by = request.user.username
        else:
            comment_by = request.user.first_name
        if commentid == "-1":
            SaleReportComment.objects.create(
                comment=comment,
                comment_by=comment_by,
                salereport_id=salereportid,
                comment_at=today

            )

            return JsonResponse({
                    "status": "Success",
                    "messages": "Comment Submited!"
            })
        else:
            try:
                sreport = SaleReportComment.objects.get(id=commentid)
                sreport.comment = comment
                sreport.comment_by = comment_by
                sreport.salereport_id = salereportid
                sreport.comment_at=today
                sreport.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Report Comment information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
    
@ajax_login_required
def ajax_reports(request):
    if request.method == "POST":
        if request.user.role == "Managers" or request.user.is_staff == True:
            reports = SaleReport.objects.all()
        else:
            reports = SaleReport.objects.filter(sale_person__iexact=request.user.username)

        return render(request, 'sales/report/ajax-report.html', {'reports': reports})


@ajax_login_required
def ajax_filter_report(request):
    if request.method == "POST":
        search_quotation = request.POST.get('search_quotation')
        daterange = request.POST.get('daterange')
        if daterange:
            startdate = datetime.datetime.strptime(daterange.split()[0],'%Y.%m.%d').replace(tzinfo=pytz.utc)
            enddate = datetime.datetime.strptime(daterange.split()[2], '%Y.%m.%d').replace(tzinfo=pytz.utc)
        search_person = request.POST.get('search_person')
        if search_quotation != "" and daterange == "" and search_person == "":
            reports = SaleReport.objects.filter(qtt_id__iexact=search_quotation)

        elif search_quotation != "" and daterange != "" and search_person == "":
            reports = SaleReport.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate)
        
        elif search_quotation != "" and daterange != "" and search_person != "":
            reports = SaleReport.objects.filter(qtt_id__iexact=search_quotation, date__gte=startdate, date__lte=enddate, sale_person__iexact=search_person)

        elif search_quotation == "" and daterange != "" and search_person == "":
            reports = SaleReport.objects.filter(date__gte=startdate, date__lte=enddate)

        elif search_quotation == "" and daterange != "" and search_person != "":
            reports = SaleReport.objects.filter(date__gte=startdate, date__lte=enddate, sale_person__iexact=search_person)

        elif search_quotation == "" and daterange == "" and search_person != "":
            reports = SaleReport.objects.filter(sale_person__iexact=search_person)

        elif search_quotation != "" and daterange == "" and search_person != "":
            reports = SaleReport.objects.filter(qtt_id__iexact=search_quotation,sale_person__iexact=search_person)

        return render(request, 'sales/report/ajax-report.html', {'reports': reports})

@ajax_login_required
def getComReport(request):
    if request.method == "POST":
        commentid = request.POST.get('commentid')
        comment = SaleReportComment.objects.get(id=commentid)
        data = {
            'comment': comment.comment

        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def reportcommentdelete(request):
    if request.method == "POST":
        commentid = request.POST.get('commentid')
        comment = SaleReportComment.objects.get(id=commentid)
        comment.delete()

        return JsonResponse({'status': 'ok'})

    


            
        

        






