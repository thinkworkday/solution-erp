import datetime
from django.conf import settings
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from accounts.models import User
from expenseclaim.models import ExpensesClaim, ExpensesClaimDetail, ExpensesClaimRecipt
from sales.decorater import ajax_login_required
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
import json
from django.views.generic.detail import DetailView
from django.db.models import Sum
from notifications.signals import notify
from reportlab.platypus import SimpleDocTemplate, Table, Image, Spacer, TableStyle, PageBreak, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.pdfgen import canvas
from reportlab.rl_config import defaultPageSize
from reportlab.lib.utils import ImageReader

# Create your views here.
@method_decorator(login_required, name='dispatch')
class ExpenseClaimView(ListView):
    model = ExpensesClaim
    template_name = "userprofile/expensesclaim-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expensesclaims'] = ExpensesClaim.objects.filter(emp_id=self.request.user.empid)
        
        
        return context

@method_decorator(login_required, name='dispatch')
class ExpenseAdminClaimView(ListView):
    model = ExpensesClaim
    template_name = "accounts/all-expensesclaim-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expensesclaims'] = ExpensesClaim.objects.all()
        
        return context

@method_decorator(login_required, name='dispatch')
class ExpenseAdminClaimDetailView(DetailView):
    model = ExpensesClaim
    template_name="accounts/all-expense-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        context['managerusers'] = User.objects.filter(role__exact="Managers")
        context['expenseclaim'] = ExpensesClaim.objects.get(id=content_pk)
        context['expense_claim_pk'] = content_pk
        expensesclaim_details = ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk)
        context['expensesclaim_details'] = expensesclaim_details
        if ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk).exists():
            subtotal = ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk).aggregate(Sum('amount'))['amount__sum']
            gst_sum = 0
            for gstrow in expensesclaim_details:
                if gstrow.gst:
                    gst_sum += gstrow.amount * 0.07
                    gstrow.gstamount = '{0:.2f}'.format(gstrow.amount * 0.07)
            context['subtotal'] = subtotal
            context['gst'] = gst_sum
            context['total_detail'] = subtotal + gst_sum
        context['expensesclaim_files'] = ExpensesClaimRecipt.objects.filter(emp_id_id=content_pk)
        return context

@ajax_login_required
def expensesclaimadd(request):
    if request.method == "POST":
        claim_no = request.POST.get('claim_no')
        submission_date = request.POST.get('submission_date')
        emp_id = request.POST.get('emp_id')
        #total = request.POST.get('total')
        expense_name = request.POST.get("expense_name")
        
        expensesid = request.POST.get('expensesid')
        if expensesid == "-1":
            try:
                expenseclaim = ExpensesClaim.objects.create(
                    submission_date=submission_date,
                    emp_id=emp_id,
                    #total=total,
                    ec_id=claim_no,
                    expenses_name=expense_name
                )
                #notification send
                sender = request.user
                description = 'Expense Claim No : ' + expenseclaim.ec_id +  ' - New Claim No was created by ' + request.user.username
                for receiver in User.objects.all():
                    if receiver.notificationprivilege.claim_no_created:
                        notify.send(sender, recipient=receiver, verb='Message', level="success", description=description)
                return JsonResponse({
                    "status": "Success",
                    "messages": "Expenses Claim information added!",
                    "expenseclaimid": expenseclaim.id
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                expenses = ExpensesClaim.objects.get(id=expensesid)
                expenses.submission_date = submission_date
                expenses.emp_id = emp_id
                #expenses.total = total
                expenses.ec_id = claim_no
                expenses.expenses_name= expense_name
                expenses.save()

                return JsonResponse({
                    "status": "Success",
                    "messages": "Expenses Claim information updated!"
                })

            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

@ajax_login_required
def expenseClaimdelete(request):
    if request.method == "POST":
        expensesid = request.POST.get('expensesid')
        expenses = ExpensesClaim.objects.get(id=expensesid)
        expenses.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def expenseClaimItemdelete(request):
    if request.method == "POST":
        itemdetailid = request.POST.get('itemdetailid')
        expensesitem = ExpensesClaimDetail.objects.get(id=itemdetailid)
        expensesitem.delete()
        if ExpensesClaimDetail.objects.filter(expensesclaim_id=expensesitem.expensesclaim_id).exists():
            subtotal = ExpensesClaimDetail.objects.filter(expensesclaim_id=expensesitem.expensesclaim_id).aggregate(Sum('amount'))['amount__sum']
            gst_sum = 0
            for gstrow in ExpensesClaimDetail.objects.filter(id=expensesitem.expensesclaim_id):
                if gstrow.gst:
                    gst_sum += gstrow.amount * 0.07
            if ExpensesClaim.objects.filter(id=expensesitem.expensesclaim_id):
                expense_amount = ExpensesClaim.objects.get(id=expensesitem.expensesclaim_id)
                expense_amount.total = subtotal + gst_sum
                expense_amount.save()
        else:
            if ExpensesClaim.objects.filter(id=expensesitem.expensesclaim_id):
                expense_amount = ExpensesClaim.objects.get(id=expensesitem.expensesclaim_id)
                expense_amount.total = 0
                expense_amount.save()
        

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def expenseClaimFiledelete(request):
    if request.method == "POST":
        fileid = request.POST.get('fileid')
        expenses = ExpensesClaimRecipt.objects.get(id=fileid)
        expenses.delete()

        return JsonResponse({'status': 'ok'})

@ajax_login_required
def getExpensesClaim(request):
    if request.method == "POST":
        expensesid = request.POST.get('expensesid')
        expenses = ExpensesClaim.objects.get(id=expensesid)
        data = {
            'submission_date': expenses.submission_date.strftime('%d %b, %Y'),
            'emp_id': expenses.emp_id,
            'total': expenses.total,
            'claim_no': expenses.ec_id,
        }
        return JsonResponse(json.dumps(data), safe=False)

@method_decorator(login_required, name='dispatch')
class ExpenseClaimDetailView(DetailView):
    model = ExpensesClaim
    template_name="userprofile/expenses-claim-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_pk = self.kwargs.get('pk')
        context['expenseclaim'] = ExpensesClaim.objects.get(id=content_pk)
        context['managerusers'] = User.objects.filter(role__exact="Managers")
        context['expense_claim_pk'] = content_pk
        expensesclaim_details = ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk)
        if ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk).exists():
            subtotal = ExpensesClaimDetail.objects.filter(expensesclaim_id=content_pk).aggregate(Sum('amount'))['amount__sum']
            gst_sum = 0
            for gstrow in expensesclaim_details:
                if gstrow.gst:
                    gst_sum += gstrow.amount * 0.07
                    gstrow.gstamount = '{0:.2f}'.format(gstrow.amount * 0.07)
            
            context['subtotal'] = subtotal
            context['gst'] = gst_sum
            context['total_detail'] = subtotal + gst_sum
        context['expensesclaim_details'] = expensesclaim_details
        context['expensesclaim_files'] = ExpensesClaimRecipt.objects.filter(emp_id_id=content_pk)
        return context

@ajax_login_required
def check_expenses_number(request):
    if request.method == "POST":
        if ExpensesClaim.objects.all().exists():
            expenses= ExpensesClaim.objects.all().order_by('-ec_id')[0]
            data = {
                "status": "exist",
                "expenses": expenses.ec_id
            }
        
            return JsonResponse(data)
        else:
            data = {
                "status": "no exist"
            }
        
            return JsonResponse(data)

@ajax_login_required
def UpdateExpenses(request):
    if request.method == "POST":
        emp_id = request.POST.get('emp_id')
        expense_name = request.POST.get('expense_name')
        submission_date = request.POST.get('submission_date')
        exp_status = request.POST.get('exp_status')
        approveby = request.POST.get('approveby')
        ec_id = request.POST.get('ec_id')

        expenseid = request.POST.get('expenseid')

        try:
            expenses = ExpensesClaim.objects.get(id=expenseid)
            expenses.ec_id = ec_id
            expenses.approveby_id = approveby
            expenses.submission_date = submission_date
            expenses.status = exp_status
            expenses.expenses_name = expense_name
            expenses.emp_id = emp_id
            expenses.save()

            return JsonResponse({
                "status": "Success",
                "messages": "Expenses Claim information updated!"
            })

        except IntegrityError as e: 
            print(e)
            return JsonResponse({
                "status": "Error",
                "messages": "Error is existed!"
            })

@ajax_login_required
def expensesclaimdetailsadd(request):
    if request.method == "POST":
        proj_id = request.POST.get('proj_id')
        vendor = request.POST.get('vendor')
        description = request.POST.get('description')
        detail_amount = request.POST.get('detail_amount')
        detail_date = request.POST.get('detail_date')
        remark = request.POST.get('remark')
        gstst = request.POST.get('detail_gst')
        detailid = request.POST.get('detailid')
        if gstst == "true":
            gststatus = True
        else:
            gststatus = False
        
        expenseid = request.POST.get('expenseid')
        if detailid == "-1":
            try:
                ExpensesClaimDetail.objects.create(
                    proj_id=proj_id,
                    vendor=vendor,
                    description=description,
                    amount=detail_amount,
                    date=detail_date,
                    gst=gststatus,
                    remark=remark,
                    expensesclaim_id=expenseid
                )
                if ExpensesClaimDetail.objects.filter(expensesclaim_id=expenseid).exists():
                    subtotal = ExpensesClaimDetail.objects.filter(expensesclaim_id=expenseid).aggregate(Sum('amount'))['amount__sum']
                    gst_sum = 0
                    for gstrow in ExpensesClaimDetail.objects.filter(expensesclaim_id=expenseid):
                        if gstrow.gst:
                            gst_sum += gstrow.amount * 0.07
                            gstrow.gstval = gstrow.amount * 0.07
                    
                    if ExpensesClaim.objects.filter(id=expenseid):
                        expense_amount = ExpensesClaim.objects.get(id=expenseid)
                        expense_amount.total = subtotal + gst_sum
                        expense_amount.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "Expenses Claim Detail information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        else:
            try:
                expensedetail = ExpensesClaimDetail.objects.get(id=detailid)
                expensedetail.proj_id=proj_id
                expensedetail.vendor=vendor
                expensedetail.description=description
                expensedetail.amount=detail_amount
                expensedetail.date=detail_date
                expensedetail.gst=gststatus
                expensedetail.remark=remark
                expensedetail.expensesclaim_id=expenseid
                expensedetail.save()
                
                if ExpensesClaimDetail.objects.filter(expensesclaim_id=expenseid).exists():
                    subtotal = ExpensesClaimDetail.objects.filter(expensesclaim_id=expenseid).aggregate(Sum('amount'))['amount__sum']
                    gst = subtotal * 0.07
                    
                    if ExpensesClaim.objects.filter(id=expenseid):
                        expense_amount = ExpensesClaim.objects.get(id=expenseid)
                        expense_amount.total = subtotal + gst
                        expense_amount.save()
                return JsonResponse({
                    "status": "Success",
                    "messages": "Expenses Claim Detail information Updated!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })
        
@ajax_login_required
def expensesclaimfilesadd(request):
    if request.method == "POST":
        receipt_no = request.POST.get('receipt_no')
        fileid = request.POST.get('fileid')
        expenseid = request.POST.get('expenseid')
        if fileid == "-1":
            try:

                ExpensesClaimRecipt.objects.create(
                    receipt_no=receipt_no,
                    receipt_file = request.FILES.get('receipt_file'),
                    receipt_name = request.FILES['receipt_file'],
                    emp_id_id=expenseid,
                    upload_by = request.user.username
                )
                return JsonResponse({
                    "status": "Success",
                    "messages": "Expenses Claim Detail information added!"
                })
            except IntegrityError as e: 
                return JsonResponse({
                    "status": "Error",
                    "messages": "Error is existed!"
                })

def exportClaimPDF(request, value):
    domain = request.META['HTTP_HOST']
    logo = Image('http://' + domain + '/static/assets/images/printlogo.png', hAlign='LEFT')
    response = HttpResponse(content_type='application/pdf')
    currentdate = datetime.date.today().strftime("%d-%m-%Y")
    pdfname = "Claim-" + str(value) + ".pdf"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(pdfname)
    story = []
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=landscape(A4), rightMargin=0.25*inch, leftMargin=0.25*inch, topMargin=1.4*inch, bottomMargin=0.25*inch, title=pdfname)
    styleSheet=getSampleStyleSheet()
    ecm = ExpensesClaim.objects.get(id=value)
    user = User.objects.get(empid__iexact=ecm.emp_id)
    ecminformation = []
    if ecm.total:
        total = ecm.total 
    else:
        total = 0
    if ecm.status:
        status = ecm.status 
    else:
        status = ""
    ecm_detail = '''
        <para align=left>
            <font size=10>Emp No:   %s</font><br/><br/>
            <font size=10>Name:   %s</font><br/><br/>
            <font size=10>Total Amount:  $ %s</font><br/>
        </para>
    ''' % (ecm.emp_id, ecm.expenses_name, total)
    ecm_title = '''
        <para align=left>
            <font size=16><b>Expenses Claim</b></font><br/>
            <font size=10>EC No: %s</font><br/>
            <font size=10>Date: %s</font><br/>
            <font size=10>Status: %s</font>
        </para>
    ''' % (ecm.ec_id, ecm.submission_date.strftime('%d/%m/%Y'), status)
    ecm_head = ParagraphStyle("justifies", leading=18)
    ecminformation.append([Paragraph(ecm_detail), Paragraph(ecm_title, ecm_head)])
    information = Table(
        ecminformation,
        style=[
            ('ALIGN',(0,0),(0,0),'LEFT'),
            ('ALIGN',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(0,0),'TOP'),
            ('VALIGN',(1,0),(1,0),'TOP'),
        ]
    )
    information._argW[0]=8.768*inch
    information._argW[1]=2.02*inch
    story.append(information)
    story.append(Spacer(1, 10))
    ecm_data = [
        [Paragraph('''<para align=center><font size=10><b>S/N</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Date</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Project No</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Vendor</b></font></para>'''),Paragraph('''<para align=center><font size=10><b>Description</b></font></para>'''),Paragraph('''<para align=center><font size=10><b>GST 7%</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Amount</b></font></para>'''), Paragraph('''<para align=center><font size=10><b>Sub Total</b></font></para>'''),Paragraph('''<para align=center><font size=10><b>Remark</b></font></para>''')]
    ]
    ecmitems = ExpensesClaimDetail.objects.filter(expensesclaim_id=value)
    index = 1
    if ecmitems.exists():
        total_gst = 0
        total_amount = 0
        total_subtotal = 0
        for ecmitem in ecmitems:
            temp_data = []
            description = '''
                <para align=center>
                    %s
                </para>
            ''' % (str(ecmitem.description))
            if ecmitem.remark:
                eremark = ecmitem.remark
            else:
                eremark = ""
            ecmdes = Paragraph(description, styleSheet["BodyText"])
            remark = '''
                <para align=center>
                    %s
                </para>
            ''' % (eremark)
            ecmremark = Paragraph(remark, styleSheet["BodyText"])
            temp_data.append(str(index))
            temp_data.append(ecmitem.date.strftime("%d-%m-%Y"))
            temp_data.append(ecmitem.proj_id)
            temp_data.append(ecmitem.vendor)
            temp_data.append(ecmdes)
            if ecmitem.gst:
                gstval = '{0:.2f}'.format(ecmitem.amount * 0.07)
                total_gst += ecmitem.amount * 0.07
                total_amount += ecmitem.amount
                total_subtotal += ecmitem.amount * 1.07
                subtotal = '{0:.2f}'.format(ecmitem.amount * 1.07)
            else:
                gstval = "-"
                total_amount += ecmitem.amount
                total_subtotal += ecmitem.amount
                subtotal = '{0:.2f}'.format(ecmitem.amount)
            temp_data.append(gstval)
            temp_data.append('{0:.2f}'.format(ecmitem.amount))
            temp_data.append(str(subtotal))
            temp_data.append(ecmremark)
            ecm_data.append(temp_data)
            index += 1
        ecm_data.append(["", "", "", "", "Total", "$ " + '{0:.2f}'.format(total_gst), "$ " +  '{0:.2f}'.format(total_amount), "$ " +  '{0:.2f}'.format(total_subtotal), ""])
        ecmtable = Table(
            ecm_data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ],
        )
    else:
        ecm_data.append(["No data available in table", "", "", "", "", "","", "",""])

        ecmtable = Table(
            ecm_data,
            style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.lavender),
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('SPAN',(0,1),(-1,-1)),
            ],
        )
    
    ecmtable._argW[0]=0.40*inch
    ecmtable._argW[1]=1.0388*inch
    ecmtable._argW[2]=1.0388*inch
    ecmtable._argW[3]=1.0388*inch
    ecmtable._argW[4]=3.73*inch
    ecmtable._argW[5]=0.732*inch
    ecmtable._argW[6]=0.732*inch
    ecmtable._argW[7]=1.0388*inch
    ecmtable._argW[8]=1.0388*inch
    ecmtable._argH[0]=0.35*inch
    story.append(ecmtable)
    story.append(Spacer(1, 10))
    if ecmitems.exists():
        story.append(PageBreak())
        story.append(Spacer(1, 15))
    style_sign = ParagraphStyle(name='left',fontSize=10, parent=styleSheet['Normal'])
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
    ecmtable1=Table(
        [
            [Paragraph('''<para align=left><font size=12><b>Submitted By: </b></font></para>'''),"","", Paragraph('''<para align=left><font size=12><b>Approved By:</b></font></para>''')],
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    ecmtable1._argW[0]=2.394*inch
    ecmtable1._argW[1]=2.50*inch
    ecmtable1._argW[2]=2.50*inch
    ecmtable1._argW[3]=3.394*inch
    story.append(ecmtable1)
    if ecm.approveby:
        if ecm.approveby.signature:
            approve_logo = Image('http://' + domain + ecm.approveby.signature.url, width=1*inch, height=1*inch, hAlign='LEFT')
            approve_name = ecm.approveby.username
        else:
            approve_name = ""
            approve_logo = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    else:
        approve_name = ""
        approve_logo = Image('http://' + domain + '/static/assets/images/logo.png', hAlign='LEFT')
    ecmtable2=Table(
        [
            [Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' %(request.user.first_name)),"",Paragraph('''<para align=left><font size=9><b>Name:</b></font></para>'''), Paragraph('''<para align=left><font size=9>%s</font></para>''' % (approve_name))]
        ],
        style=[
            ('VALIGN',(0,0),(0,-1),'TOP'),
        ],
    )
    ecmtable2._argW[0]=0.8*inch
    ecmtable2._argW[1]=2.994*inch
    ecmtable2._argW[2]=3.6*inch
    ecmtable2._argW[3]=0.8*inch
    ecmtable2._argW[4]=2.594*inch
    story.append(Spacer(1, 10))
    story.append(ecmtable2)
    ecmtable3=Table(
        [
            [Paragraph(sign_title1, style_sign), "","", Paragraph(sign_title2, style_sign), ""],
            ["", sign_logo,"", "", approve_logo]
        ],
        style=[
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ],
    )
    story.append(Spacer(1, 10))
    ecmtable3._argW[0]=1.0*inch
    ecmtable3._argW[1]=2.794*inch
    ecmtable3._argW[2]=3.6*inch
    ecmtable3._argW[3]=1.0*inch
    ecmtable3._argW[4]=2.394*inch
    story.append(ecmtable3)
    
    doc.build(story, canvasmaker=LandScapeNumberedCanvas)
    response.write(buff.getvalue())
    buff.close()

    return response

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

@ajax_login_required
def getExpenseItem(request):
    if request.method == "POST":
        exidetailid = request.POST.get('exidetailid')
        expitem = ExpensesClaimDetail.objects.get(id=exidetailid)
        data = {
            'date': expitem.date.strftime('%d %b, %Y'),
            'proj_id': expitem.proj_id,
            'vendor': expitem.vendor,
            'description': expitem.description,
            'amount': expitem.amount,
            'remark': expitem.remark,
            'gst': expitem.gst,

        }
        return JsonResponse(json.dumps(data), safe=False)

        
