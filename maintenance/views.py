import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
import pytz
from django.views import generic
from maintenance.models import Device, MainSRSignature, MainSr, MainSrItem, Maintenance, MaintenanceFile, Schedule
from accounts.models import Uom, User
from maintenance.resources import MainSrItemResource, MaintenanceResource
from sales.decorater import ajax_login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import IntegrityError
import json
from django.views.generic.detail import DetailView
from django.db.models import Q
from dateutil import parser as date_parser
import pandas as pd
import os

from sales.models import Company, Contact, Quotation, Scope

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
class MaintenanceView(ListView):
    model = Maintenance
    template_name = "maintenance/maintenance-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maintenances'] = Maintenance.objects.all()
        context['contacts'] = User.objects.all()
        return context


@ajax_login_required
def maintenanceadd(request):
    if request.method == "POST":
        main_no = request.POST.get('main_no')
        in_incharge = request.POST.get('in_incharge')
        end_date = request.POST.get('end_date')
        start_date = request.POST.get('start_date')
        customer = request.POST.get('customer')
        maintenanceid = request.POST.get('maintenanceid')
        if maintenanceid == "-1":
            try:
                Maintenance.objects.create(
                    main_no=main_no,
                    end_date=end_date,
                    in_incharge=in_incharge,
                    start_date=start_date,
                    contact_person_id=customer,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Company information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already this email is existed!"
                })
        else:
            try:
                mainte = Maintenance.objects.get(id=maintenanceid)
                mainte.main_no = main_no
                mainte.in_incharge = in_incharge
                mainte.end_date = end_date
                mainte.start_date = start_date
                mainte.contact_person_id = customer
                mainte.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Maintenance information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def getMaintenanace(request):
    if request.method == "POST":
        maintenanceid = request.POST.get('maintenanceid')
        main = Maintenance.objects.get(id=maintenanceid)
        data = {
            'main_no': main.main_no,
            'start_date': main.start_date.strftime('%d %b, %Y'),
            'end_date': main.end_date.strftime('%d %b, %Y'),
            'contactperson': str(main.contact_person_id),
            'in_incharge': main.in_incharge
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def maintenancedelete(request):
    if request.method == "POST":
        maintenanceid = request.POST.get('maintenanceid')
        main = Maintenance.objects.get(id=maintenanceid)
        main.delete()

        return JsonResponse({'status': 'ok'})

@method_decorator(login_required, name='dispatch')
class MaintenanceDetailView(DetailView):
    model = Maintenance
    template_name="maintenance/maintenance-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')  
        summary = Maintenance.objects.get(id=content_pk)
        context['maintenance'] = summary
        context['maintenance_pk'] = content_pk
        context['contacts'] = Contact.objects.all()
        context['companies'] = Company.objects.all()
        context['uoms'] = Uom.objects.all()
        context['projects_incharge'] = User.objects.filter(Q(role__icontains='Managers') | Q(role__icontains='Engineers') | Q(is_staff=True))
        context['filelist'] = MaintenanceFile.objects.filter(maintenance_id=content_pk)
        context['srlist'] = MainSr.objects.filter(maintenance_id=content_pk)
        quotation = summary.quotation
        maintenanceitems = Scope.objects.filter(quotation_id=quotation.id,parent=None)
        context['maintenanceitems'] = maintenanceitems
        context["devices"] = Device.objects.filter(maintenance_id=content_pk)  
        context['suppliers'] = Company.objects.filter(associate="Supplier")
        context['schedules'] = Schedule.objects.filter(maintenance_id=content_pk)     
        
        return context

@ajax_login_required
def UpdateMain(request):
    if request.method == "POST":
        
        company_name = request.POST.get('company_name')
        worksite_address = request.POST.get('worksite_address')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        tel = request.POST.get('tel')
        fax = request.POST.get('fax')
        proj_incharge = request.POST.get('proj_incharge')
        site_incharge = request.POST.get('site_incharge')
        site_tel = request.POST.get('site_tel')
        RE = request.POST.get('re')
        main_no = request.POST.get('main_no')
        note = request.POST.get('note')
        quot_no = request.POST.get('quot_no')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        main_status = request.POST.get('main_status')
        mainid = request.POST.get('mainid')
        
        try:
            main = Maintenance.objects.get(id=mainid)
            
            main.company_name_id=company_name
            main.worksite_address=worksite_address
            main.contact_person_id=contact_person
            main.email=email
            main.tel=tel
            main.fax=fax
            main.quot_no=quot_no
            main.main_no=main_no
            main.proj_incharge=proj_incharge
            main.site_incharge=site_incharge
            main.site_tel=site_tel
            main.start_date=start_date
            main.end_date=end_date
            main.main_status=main_status
            main.RE=RE
            main.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Maintenance information updated!"
            })
        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@ajax_login_required
def ajax_add_main_file(request):
    if request.method == "POST":
        name = request.POST.get('filename')
        fileid = request.POST.get('fileid')
        maintenanceid = request.POST.get('maintenanceid')
        if fileid == "-1":
            try:
                MaintenanceFile.objects.create(
                    name=name,
                    document = request.FILES.get('document'),
                    uploaded_by_id=request.user.id,
                    maintenance_id = maintenanceid,
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
def deleteMainFile(request):
    if request.method == "POST":
        filedel_id = request.POST.get('filedel_id')
        mainfile = MaintenanceFile.objects.get(id=filedel_id)
        mainfile.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def ajax_check_main_srnumber(request):
    if request.method == "POST":
        if MainSr.objects.all().exists():
            mainsr= MainSr.objects.all().order_by('-sr_no')[0]
            data = {
                "status": "exist",
                "sr_no": mainsr.sr_no.replace('CSR','').split()[0]
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def mainsradd(request):
    if request.method == "POST":
        sr_no = request.POST.get('sr_no')
        date = request.POST.get('srdate')
        if date == "":
            date = None
        maintenanceid = request.POST.get('maintenanceid')
        srid = request.POST.get('srid')
        # if request.user.signature != "":
        #     status = "Signed"
        # else:
        #     status = "Open"
        if srid == "-1":
            try:
                MainSr.objects.create(
                    sr_no=sr_no,
                    date=date,
                    status="Open",
                    # uploaded_by_id=request.user.id,
                    maintenance_id=maintenanceid,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Report information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR is existed!"
                })
        else:
            try:
                sr = MainSr.objects.get(id=srid)
                sr.sr_no = sr_no
                sr.date = date
                # sr.status = status
                # sr.uploaded_by_id=request.user.id
                sr.maintenance_id = maintenanceid
                sr.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Service Report information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already SR is existed!"
                })

@ajax_login_required
def mainsrdocadd(request):
    if request.method == "POST":
        maintenanceid = request.POST.get('maintenanceid')
        srdocid = request.POST.get('srdocid')
        try:
            mainsr = MainSr.objects.get(id=srdocid)
            mainsr.uploaded_by_id=request.user.id
            mainsr.maintenance_id = maintenanceid
            if request.FILES.get('document'):
                mainsr.document = request.FILES.get('document')
                mainsr.status = "Signed"
            mainsr.save()

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
def deleteMainSR(request):
    if request.method == "POST":
        srdel_id = request.POST.get('srdel_id')
        mainsrdata = MainSr.objects.get(id=srdel_id)
        mainsrdata.delete()

        return JsonResponse({'status': 'ok'})

@method_decorator(login_required, name='dispatch')
class MainSrDetailView(DetailView):
    model = MainSr
    pk_url_kwarg = 'srpk'
    template_name="maintenance/service-report-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        main_pk = self.kwargs.get('pk')
        sr_pk = self.kwargs.get('srpk')
        summary = Maintenance.objects.get(id=main_pk)
        context['summary'] = summary
        context['maintenance_pk'] = main_pk
        context['service_pk'] = sr_pk
        service_report = MainSr.objects.get(id=sr_pk)
        context['contacts'] = Contact.objects.all()
        context['uoms'] = Uom.objects.all()
        context['service_report'] = service_report
        quotation = Quotation.objects.get(qtt_id__iexact=summary.quot_no)
        sritems = Scope.objects.filter(quotation_id=quotation.id,parent=None)
        #context['sritems'] = MainSrItem.objects.filter(maintenance_id=main_pk, sr_id=sr_pk)
        context['sritems'] = sritems
        context['quotation'] = quotation
        if(MainSRSignature.objects.filter(maintenance_id=main_pk, sr_id=sr_pk).exists()):
            context['srsignature'] = MainSRSignature.objects.get(maintenance_id=main_pk, sr_id=sr_pk)
        else:
            context['srsignature'] = None
        context['projectitemall'] = Scope.objects.filter(quotation_id=quotation.id)
        return context

@ajax_login_required
def ajax_update_main_service_report(request):
    if request.method == "POST":
        srtype = request.POST.get('srtype')
        srpurpose = request.POST.get('srpurpose')
        srsystem = request.POST.get('srsystem')
        timein = request.POST.get('timein')
        timeout = request.POST.get('timeout')
        remark = request.POST.get('remark')
        servicepk = request.POST.get('servicepk')

        srdata = MainSr.objects.get(id=servicepk)
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
def mainsrItemAdd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        qty = request.POST.get('qty')
        uom = request.POST.get('uom')
        sritemid = request.POST.get('sritemid')
        maintenanceid = request.POST.get('maintenanceid')
        srid = request.POST.get('srid')

        if sritemid == "-1":
            try:
                MainSrItem.objects.create(
                    description=description,
                    qty=qty,
                    uom=uom,
                    maintenance_id=maintenanceid,
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
                sritem = MainSrItem.objects.get(id=sritemid)
                sritem.description = description
                sritem.qty = qty
                sritem.uom = uom
                sritem.maintenance_id = maintenanceid
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
def getMainSrItem(request):
    if request.method == "POST":
        sritemid = request.POST.get('sritemid')
        sritem = MainSrItem.objects.get(id=sritemid)
        data = {
            'description': sritem.description,
            'qty': sritem.qty,
            'uom': sritem.uom,
        }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def deleteMainSRItem(request):
    if request.method == "POST":
        sritem_del_id = request.POST.get('del_id')
        sritem = MainSrItem.objects.get(id=sritem_del_id)
        sritem.delete()

        return JsonResponse({'status': 'ok'})

def ajax_export_main_sr_item(request, maintenanceid, srid):
    resource = MainSrItemResource()
    queryset = MainSrItem.objects.filter(maintenance_id=maintenanceid, sr_id=srid)
    dataset = resource.export(queryset)
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project_maintenance_sr_items.csv"'
    return response

@method_decorator(login_required, name='dispatch')
class MainSrSignatureCreate(generic.CreateView):
    model = MainSRSignature
    fields = '__all__'
    template_name="maintenance/service-signature.html"

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            MainSRSignature.objects.create(
                signature=request.POST.get('signature'),
                name=sign_name,
                nric = sign_nric,
                update_date = datetime.datetime.strptime(sign_date,'%d %b %Y'),
                sr_id=self.kwargs.get('srpk'),
                maintenance_id=self.kwargs.get('pk')
            )
            return HttpResponseRedirect('/maintenance-detail/' + self.kwargs.get('pk') + '/service-report-detail/' + self.kwargs.get('srpk'))

@method_decorator(login_required, name='dispatch')
class MainSrSignatureUpdate(generic.UpdateView):
    model = MainSRSignature
    pk_url_kwarg = 'signpk'
    fields = '__all__'
    template_name="maintenance/service-signature.html"
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            sign_name = request.POST.get("sign_name")
            sign_nric = request.POST.get("sign_nric")
            sign_date = request.POST.get("sign_date")
            srSignature = MainSRSignature.objects.get(id=self.kwargs.get('signpk'))
            srSignature.signature = request.POST.get('signature')
            srSignature.name = sign_name
            srSignature.nric = sign_nric
            srSignature.update_date = datetime.datetime.strptime(sign_date.replace(',', ""),'%d %b %Y').date()
            srSignature.sr_id = self.kwargs.get('srpk')
            srSignature.maintenance_id = self.kwargs.get('pk')
            srSignature.save()

            return HttpResponseRedirect('/maintenance-detail/' + self.kwargs.get('pk') + '/service-report-detail/' + self.kwargs.get('srpk'))

@ajax_login_required
def maindeviceadd(request):
    if request.method == "POST":
        hardware_code = request.POST.get('hardware_code')
        hardware_desc = request.POST.get('hardware_desc')
        serial_number = request.POST.get('serial_number')
        uom = request.POST.get('uom')
        expiry_date = request.POST.get('expiry_date')
        licensing_date = request.POST.get('licensing_date')
        if licensing_date:
            licensing = licensing_date
        else:
            licensing = None
        remark = request.POST.get('remark')
        stock_qty = request.POST.get('stock_qty')
        brand = request.POST.get('brand')
        supplier = request.POST.get('supplier')
        maintenanceid = request.POST.get('maintenanceid')
        deviceid = request.POST.get('deviceid')
        if deviceid == "-1":
            try:
                obj = Device(
                    hardware_code=hardware_code,
                    hardware_desc=hardware_desc,
                    serial_number=serial_number,
                    uom=uom,
                    expiry_date=expiry_date,
                    licensing_date=licensing,
                    remark=remark,
                    qty=stock_qty,
                    brand=brand,
                    supplier_name=supplier,
                    maintenance_id=maintenanceid
                )
                obj.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "Device information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Hardware code Already is existed!"
                })
        else:
            try:
                device = Device.objects.get(id=deviceid)
                device.hardware_code=hardware_code
                device.hardware_desc = hardware_desc
                device.serial_number = serial_number
                device.uom = uom
                device.supplier_name = supplier
                device.expiry_date=expiry_date
                device.licensing_date=licensing
                device.remark = remark
                device.qty = stock_qty
                device.brand=brand
                device.maintenance_id=maintenanceid
                
                device.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Device information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def getDevice(request):
    if request.method == "POST":
        deviceid = request.POST.get('deviceid')
        device = Device.objects.get(id=deviceid)
        if device.licensing_date:
            data = {
                'hardware_code': device.hardware_code,
                'serial_number': device.serial_number,
                'hardware_desc': device.hardware_desc,
                'stock_qty': device.qty,
                'expiry_date': device.expiry_date.strftime('%d %b, %Y'),
                'licensing_date': device.licensing_date.strftime('%d %b, %Y'),
                'remark': device.remark,
                'uom': device.uom,
                'brand': device.brand,
                'supplier': device.supplier_name

            }
        else:
            data = {
                'hardware_code': device.hardware_code,
                'serial_number': device.serial_number,
                'hardware_desc': device.hardware_desc,
                'stock_qty': device.qty,
                'expiry_date': device.expiry_date.strftime('%d %b, %Y'),
                'licensing_date': '',
                'remark': device.remark,
                'uom': device.uom,
                'brand': device.brand,
                'supplier': device.supplier_name

            }
        return JsonResponse(json.dumps(data), safe=False)

@ajax_login_required
def devicedelete(request):
    if request.method == "POST":
        deviceid = request.POST.get('deviceid')
        device = Device.objects.get(id=deviceid)
        device.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def scheduleadd(request):
    if request.method == "POST":
        description = request.POST.get('description')
        remark = request.POST.get('remark')
        reminder = request.POST.get('reminder')
        date = request.POST.get('date')
        if date == "":
            date = None
        maintenanceid = request.POST.get('maintenanceid')
        scheduleid = request.POST.get('scheduleid')
        if scheduleid == "-1":
            try:
                Schedule.objects.create(
                    description=description,
                    remark=remark,
                    reminder=reminder,
                    date=date,
                    maintenance_id=maintenanceid,
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Schedule information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Bom is existed!"
                })
        else:
            try:
                schedule = Schedule.objects.get(id=scheduleid)
                schedule.description = description
                schedule.reminder = reminder
                schedule.date = date
                schedule.remark=remark
                schedule.maintenance_id = maintenanceid
                schedule.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Schedule information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Already Schedule is existed!"
                })

@ajax_login_required
def scheduledelete(request):
    if request.method == "POST":
        scheduleid = request.POST.get('scheduleid')
        schedule = Schedule.objects.get(id=scheduleid)
        schedule.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getSchedule(request):
    if request.method == "POST":
        scheduleid = request.POST.get('scheduleid')
        schedule = Schedule.objects.get(id=scheduleid)
        data = {
            'date': schedule.date.strftime('%d %b, %Y'),
            'description': schedule.description,
            'remark': schedule.remark,
            'reminder': schedule.reminder
        }
        
        return JsonResponse(json.dumps(data), safe=False)

def exportMainSrPDF(request, value):
    sr = MainSr.objects.get(id=value)
    maintenance = sr.maintenance
    quotation = maintenance.quotation
    sritems = MainSrItem.objects.filter(sr_id=value)

    domain = request.META['HTTP_HOST']
    logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    response = HttpResponse(content_type='application/pdf')
    #currentdate = datetime.date.today().strftime("%d-%m-%Y")
    pdfname = sr.sr_no + ".pdf"
    response['Content-Disposition'] = 'attachment; filename={}'.format(pdfname)
    story = []
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=portrait(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.25*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    data= [
        [Paragraph('''<para align=center><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Description</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>UOM</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>QTY</b></font></para>''')],
    ]

    if maintenance.start_date:
        pdate =  maintenance.start_date.strftime('%d %b, %Y')
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
    srinfordata = [
        [Paragraph('''<para align=left><font size=10><b>To: </b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.company_name)), "", "", "" , Paragraph('''<para align=center><font size=16><b>SERVICE REPORT</b></font></para>''')],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)),"", "", "" , ""],
        ["", Paragraph('''<para align=left><font size=10>%s</font></para>''' % (quotation.address + "  " + qunit)), "" ,"", "", Paragraph('''<para align=left><font size=10><b>SR No:</b> %s</font></para>''' % (sr.sr_no))],
        ["", "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Maintenance No.:</b> %s</font></para>''' % (maintenance.main_no))],
        [Paragraph('''<para align=left><font size=10><b>Attn :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (maintenance.contact_person.salutation + " " + maintenance.contact_person.contact_person)),Paragraph('''<para align=left><font size=10><b>Email :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (maintenance.email)), "", Paragraph('''<para align=left><font size=10><b>Date:</b> %s</font></para>''' % (sr.date.strftime('%d/%m/%Y')))],
        [Paragraph('''<para align=left><font size=10><b>Tel :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (maintenance.tel)), Paragraph('''<para align=left><font size=10><b>Fax :</b></font></para>'''), Paragraph('''<para align=left><font size=10>%s</font></para>''' % (maintenance.fax)), "", ""],
        ["", "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10><b>Worksite: </b> %s</font></para>''' % (maintenance.worksite_address)), "", "" ,"", "", ""],
        ["", "", "" ,"", "", ""],
        [Paragraph('''<para align=left><font size=10><b>Service Type: </b> %s</font></para>''' % (srtype)), "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Time In: </b> %s</font></para>''' % (time_in))],
        [Paragraph('''<para align=left><font size=10><b>System: </b> %s</font></para>'''  % (srsystem)), "", "" ,"", "", Paragraph('''<para align=left><font size=10><b>Time Out: </b> %s</font></para>''' % (time_out))],
        [Paragraph('''<para align=left><font size=10><b>Purpose: </b> %s</font></para>''' % (srpurpose)), "", "" ,"", "", ""],
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
            ('SPAN',(3,4),(4,4)),
            ('SPAN',(0,7),(-1,7)),
            ('SPAN',(0,9),(-2,9)),
            ('SPAN',(0,10),(-2,10)),
            ('SPAN',(0,11),(-1,11)),

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
    srsignature = MainSRSignature.objects.filter(sr_id=value)
    
    if srsignature.exists():
        srsign_data = MainSRSignature.objects.get(sr_id=value)
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

def ajax_export_maintenance(request):
    resource = MaintenanceResource()
    dataset = resource.export()
    response = HttpResponse(dataset.csv, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance-summary.csv"'
    return response

def ajax_import_maintenance(request):
    
    if request.method == 'POST':
        org_column_names = ['main_no', 'customer', 'start_date', 'end_date', 'in_incharge', 'main_status']
        
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
                exist_count = Maintenance.objects.filter(main_no=row["main_no"]).count()
                if exist_count == 0:
                    try:
                        maintenance = Maintenance(
                            main_no=row["main_no"],
                            customer=row["customer"],
                            start_date=datetime.datetime.strptime(row["start_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc), 
                            end_date=datetime.datetime.strptime(row["end_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc), 
                            in_incharge=row["in_incharge"],
                            main_status=row["main_status"],
                        )
                        maintenance.save()
                        success_record += 1
                    except Exception as e:
                        print(e)
                        failed_record += 1
                else:
                    try:
                        maintenance = Maintenance.objects.filter(main_no=row["main_no"])[0]
                        maintenance.main_no = row["main_no"]
                        maintenance.customer = row["customer"]
                        maintenance.start_date=datetime.datetime.strptime(row["start_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc)
                        maintenance.end_date=datetime.datetime.strptime(row["end_date"],'%Y-%m-%d').replace(tzinfo=pytz.utc)
                        maintenance.in_incharge=row["in_incharge"]
                        maintenance.main_status=row["main_status"]
                        
                        maintenance.save()
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