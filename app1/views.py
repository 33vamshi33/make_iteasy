from django.shortcuts import render,redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse,reverse_lazy
from django.contrib.auth import authenticate,login,logout
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,DetailView,CreateView
from app1.models import Customer,Broker,User,connection,feedback,Message
from app1.forms import userform,brokerform,searchform,userprofileform,feedbackform,loginform
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from test1 import settings
from django.core.mail import send_mail
from django.db.models import Avg,Count
from django.contrib.auth.forms import AuthenticationForm
# Create your views here.

def customerauth(user):
    if user.id is not None:
        return user.is_customer and user.is_authenticated
    return False

def brokerauth(user):
    if user.id is not None:
        return user.is_broker and user.is_authenticated
    return False

def iscustomer(fn=None):
    decorator=user_passes_test(customerauth)
    if fn:
        return decorator(fn)
    return decorator

def isbroker(fn=None):
    decorator=user_passes_test(brokerauth)
    if fn:
        return decorator(fn)
    return decorator

class homepage(TemplateView):
    template_name="homepage.html"

@iscustomer
def customerdetail(request):
    connection.objects.filter(broker_status="order not accepted").update(broker_status="request pending")
    brokers=Broker.objects.order_by("-average_rating")
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    if request.method=='POST':
        if "connect" in request.POST:
            newconnection=connection()
            presentbroker=Broker.objects.get(user__username=request.POST.get("broker"))
            presentcustomer=Customer.objects.get(user=request.user)
            prevconnection=connection.objects.filter(customer=presentcustomer).filter(broker=presentbroker).filter(customer_status="order pending")
            newconnection.broker=presentbroker
            newconnection.customer=presentcustomer
            newconnection.customer_status="order pending"
            newconnection.broker_status="request pending"
            newconnection.description=request.POST.get('description')
            newconnection.created_time=timezone.now()
            newconnection.modified_time=timezone.now()
            if len(prevconnection) == 0 :
                subject="Hey"+ newconnection.broker.user.username +"! a new request from a customer that is  "+newconnection.description
                body=f"makeiteasy helps it really helps"
                receiverlist=[newconnection.broker.user.email,]
                # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
                newconnection.save()
            return redirect(reverse('app1:customer_pendingorders'))

        else :
            department=request.POST.get('department')
            location=request.POST.get('location')
            mylist=[]
            alllist=[0,1,2,3,4,5,6]
            for i in alllist:
                if str(i) in request.POST:
                    mylist.append(i)
            if len(mylist) == 0:
                mylist=alllist 
            brokers=Broker.objects.filter(department_name__startswith=department).filter(location__startswith=location)
            tempbroker=brokers
            empty=Broker.objects.none()
            for i in mylist:
                newbroker=tempbroker.filter(days__contains=i)
                empty=empty.union(newbroker)
            brokers=empty
            brokers=brokers.order_by("-average_rating")
    context={
        "unreadconnections":unreadconnections,
        "unreadmessages":unreadmessages,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    context["brokers"] = brokers
    context["customer"]=request.user
    return render(request,"customer/home.html",context)
    

@isbroker
@csrf_exempt
def brokerdetail(request):
    broker=Broker.objects.get(user=request.user)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    mylist=broker.days
    if request.method=='POST':
        mylist=[]
        alllist=[0,1,2,3,4,5,6]
        for i in alllist:
            if str(i) in request.POST:
                mylist.append(i)
        broker.days=mylist
        broker.save()
    context={
        "mylist":mylist,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/home.html",context=context)

def customerlogin(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('app1:customer_home')
    else:
        form = AuthenticationForm()
    return render(request, 'customer/login.html', {'loginform': form})

def brokerlogin(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('app1:broker_home')
    else:
        form = AuthenticationForm()
    return render(request, 'broker/login.html', {'loginform': form})

def customersignup(request):
    registered=False
    if request.method=='POST':
        user_form=userform(data=request.POST)
        user_profileform=userprofileform(request.POST,request.FILES)

        if user_form.is_valid() and user_profileform.is_valid() :

            user=user_form.save()
            user.is_customer=True
            if 'picture' in request.FILES :
                user.picture=request.FILES['picture']
            user.save()
            customer=Customer()
            customer.user=user
            customer.save()
            subject="thanks for registering  with makeiteasy"
            body=f"makeiteasy helps it really helps"
            receiverlist=[user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            registered=True
        else:
            print(user_form.errors)
            print(user_profileform.errors)

    else:

        user_form=userform()
        user_profileform=userprofileform()
    if registered:
        return HttpResponseRedirect(reverse('app1:customer_login'))
    return render(request,'customer/signup.html',{'registered':registered,
                                                    'userform':user_form,
                                                    'userprofileform':user_profileform })


def brokersignup(request):
    registered=False

    if request.method=='POST':
        user_form=userform(data=request.POST)
        broker_form=brokerform(data=request.POST)
        user_profileform=userprofileform(request.POST,request.FILES)
        if user_form.is_valid() and broker_form.is_valid() and user_profileform.is_valid() :

            user=user_form.save()
            user.is_broker=True
            if 'picture' in request.FILES :
                user.picture=request.FILES['picture']
            user.save()
            
            broker=broker_form.save(commit=False)
            broker.user=user
            broker.save()
            registered=True
        else:
            print(user_form.errors)
            print(broker_form.errors)

    else:

        user_form=userform()
        broker_form=brokerform()
        user_profileform=userprofileform()
    if registered:

        return HttpResponseRedirect(reverse('app1:broker_login'))
    return render(request,'broker/signup.html',{'registered':registered,
                                                'userform':user_form ,
                                                'brokerform':broker_form,
                                                "userprofileform":user_profileform})


@iscustomer
def customerlogout(request):
    logout(request)
    return redirect(reverse('app1:homepage'))

@isbroker
def brokerlogout(request):
    logout(request)
    return redirect(reverse('app1:homepage'))

@iscustomer
def customerorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    acceptedorders=orderslist.filter(customer_status="order accepted")
    rejectedorders=orderslist.filter(customer_status="order rejected")
    pendingorders=orderslist.filter(customer_status="order pending")
    completedorders=orderslist.filter(customer_status="order completed")
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    #qs=connection.objects.filter(customer__user=request.user).update(is_read=True)
    context={
        "orders":orderslist,
        "acceptedorders":acceptedorders,
        "rejectedorders":rejectedorders,
        "pendingorders":pendingorders,
        "completedorders":completedorders,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedorders),
        "rsize":len(rejectedorders),
        "psize":len(pendingorders),
        "csize":len(completedorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/orders.html",context=context)

@iscustomer
def customerpendingorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    pendingorders=orderslist.filter(customer_status="order pending")
    pendingorders.update(is_customerread=True)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "pendingorders":pendingorders,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "psize":len(pendingorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/pendingorders.html",context=context)

@iscustomer
def customeracceptedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    acceptedorders=orderslist.filter(customer_status="order accepted")
    acceptedorders.update(is_customerread=True)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "acceptedorders":acceptedorders,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/acceptedorders.html",context=context)

@iscustomer
def customerrejectedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    rejectedorders=orderslist.filter(customer_status="order rejected")
    rejectedorders.update(is_customerread=True)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "rejectedorders":rejectedorders,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "rsize":len(rejectedorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/rejectedorders.html",context=context)

@iscustomer
def customercompletedorders(request):
    presentcustomer=Customer.objects.get(user=request.user)
    orderslist=connection.objects.filter(customer=presentcustomer)
    completedorders=orderslist.filter(customer_status="order completed")
    completedorders.update(is_customerread=True)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "completedorders":completedorders,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "csize":len(completedorders),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/completedorders.html",context=context)

@isbroker
@csrf_exempt
def brokerrequests(request):
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            subject="Yahoo! your order is accepted"
            body=f"makeiteasy helps, it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()

            # return render(request,"broker/requests.html",context=context)
        elif "reject" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order rejected"
            presentconnection.broker_status="request rejected"
            presentconnection.modified_time=timezone.now()
            subject="Sorry! your order has been rejected"
            body=f"makeiteasy helps it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()
            # return render(request,"broker/requests.html",context=context)
        elif "completed" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order completed"
            presentconnection.broker_status="request completed"
            presentconnection.modified_time=timezone.now()
            subject="Hurray! your order is completed"
            body=f"makeiteasy helps it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()
        else:
            pass
            # return render(request,"broker/requests.html",context=context)
        
    presentbroker=Broker.objects.get(user=request.user)
    requestslist=connection.objects.filter(broker=presentbroker)
    acceptedrequests=requestslist.filter(broker_status="request accepted")
    rejectedrequests=requestslist.filter(broker_status="request rejected")
    pendingrequests=requestslist.filter(broker_status="request pending")
    completedrequests=requestslist.filter(broker_status="request completed")
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "requests":requestslist,
        "acceptedrequests":acceptedrequests,
        "rejectedrequests":rejectedrequests,
        "pendingrequests":pendingrequests,
        "completedrequests":completedrequests,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedrequests),
        "rsize":len(rejectedrequests),
        "psize":len(pendingrequests),
        "csize":len(completedrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/requests.html",context=context)

@isbroker
def brokerpendingrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    requestlist=connection.objects.filter(broker=presentbroker)
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            subject="Yahoo! your order is accepted"
            body=f"makeiteasy helps, it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()
            return redirect(reverse("app1:broker_acceptedrequests"))

            # return render(request,"broker/requests.html",context=context)
        elif "reject" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order rejected"
            presentconnection.broker_status="request rejected"
            presentconnection.modified_time=timezone.now()
            subject="Sorry! your order has been rejected"
            body=f"makeiteasy helps it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()
            return redirect(reverse("app1:broker_rejectedrequests"))

        else:
            pass

    pendingrequests=connection.objects.filter(broker=presentbroker,broker_status="request pending")
    pendingrequests.update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "pendingrequests":pendingrequests,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "psize":len(pendingrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/pendingrequests.html",context)

@isbroker
def brokeracceptedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "completed" in request.POST and presentconnection is not None:
                presentconnection.customer_status="order completed"
                presentconnection.broker_status="request completed"
                presentconnection.modified_time=timezone.now()
                subject="Hurray! your order is completed"
                body=f"makeiteasy helps it really helps"
                receiverlist=[presentconnection.customer.user.email,]
                # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
                presentconnection.save()
    acceptedrequests=connection.objects.filter(broker=presentbroker,broker_status="request accepted")
    acceptedrequests.update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "acceptedrequests":acceptedrequests,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "asize":len(acceptedrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/acceptedrequests.html",context)

@isbroker
def brokercompletedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    completedrequests=connection.objects.filter(broker=presentbroker,broker_status="request completed")
    completedrequests.update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "completedrequests":completedrequests,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "csize":len(completedrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/completedrequests.html",context)

@isbroker
def brokerrejectedrequests(request):
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        presentconnection=connection.objects.filter(pk=request.POST.get("connection")).first()
        if "accept" in request.POST and presentconnection is not None:
            presentconnection.customer_status="order accepted"
            presentconnection.broker_status="request accepted"
            presentconnection.modified_time=timezone.now()
            subject="Yahoo! your order is accepted"
            body=f"makeiteasy helps, it really helps"
            receiverlist=[presentconnection.customer.user.email,]
            # send_mail(subject,message=body,from_email=settings.EMAIL_HOST_USER,recipient_list=receiverlist,fail_silently=False)
            presentconnection.save()

    rejectedrequests=connection.objects.filter(broker=presentbroker,broker_status="request rejected")
    rejectedrequests.update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "rejectedrequests":rejectedrequests,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "rsize":len(rejectedrequests),
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/rejectedrequests.html",context)

@iscustomer
def customerprofile(request):
    picture_form=userprofileform()
    if request.method == 'POST' and request.user.id is not None:
        customer=Customer.objects.get(user=request.user)
        user=User.objects.filter(username=request.user.username).first()
        username=request.POST.get("username")
        password=request.POST.get("password")
        phonenumber=request.POST.get("phonenumber")
        email=request.POST.get("email")
        lists=User.objects.filter(username=username)
        if username is not None and len(username) and len(lists) ==0 :
            user.username=username
        if password is not None and len(password) :
            user.set_password(password)
        if email is not None and len(email):
            user.email=email
        picture_form=userprofileform(request.POST,request.FILES)

        if picture_form.is_valid() and 'picture' in request.FILES :
            print("in it")
            user.picture=request.FILES['picture']
        user.save()
        customer.user=user
        customer.save()
        print("completed")
        return redirect(reverse("app1:customer_home"))
    customer=Customer.objects.get(user=request.user)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    context={
        "customer":customer,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "pictureform":picture_form,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/profile.html",context=context)

@isbroker
def brokerprofile(request):
    picture_form=userprofileform()
    if request.method == 'POST' and request.user.id is not None:
        broker=Broker.objects.get(user=request.user)
        user=User.objects.filter(username=request.user.username).first()
        username=request.POST.get("username")
        password=request.POST.get("password")
        phonenumber=request.POST.get("phonenumber")
        email=request.POST.get("email")
        departmentname=request.POST.get("departmentname")
        location=request.POST.get("location")
        lists=User.objects.filter(username=username)
        if len(username) and len(lists) ==0 :
            user.username=username
        if len(password) :
            user.set_password(password)
        if len(email):
            user.email=email

        picture_form=userprofileform(request.POST,request.FILES)

        if picture_form.is_valid() and 'picture' in request.FILES :
            user.picture=request.FILES['picture']
        user.save()
        broker.user=user
        broker.department_name=departmentname
        broker.location=location
        broker.save()
        return redirect(reverse("app1:broker_home"))

    broker=Broker.objects.get(user=request.user)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "broker":broker,
        "pictureform":picture_form,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/profile.html",context)

@iscustomer
def customerreview(request,pk):
    feedback_form=feedbackform()
    customer=Customer.objects.get(user=request.user)
    broker=Broker.objects.get(pk=pk)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    if request.method=='POST' :
        description=request.POST.get("description")
        rating=request.POST.get("rating")
        newfeedback=feedback()
        oldfeedback=feedback.objects.filter(customer=customer,broker=broker).first()
        if oldfeedback is   None:
            newfeedback.customer=customer
            newfeedback.broker=broker
            newfeedback.description=description
            newfeedback.rating=rating
            newfeedback.created_time=timezone.now()
            newfeedback.save()
            reviews=feedback.objects.filter(broker=broker)
            presentbrokerfeedback=feedback.objects.filter(broker=broker)
            avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
            broker.average_rating=avgrating
            broker.save()
            return redirect("app1:customer_home")
        else :
            oldfeedback.description=description
            oldfeedback.rating=rating
            oldfeedback.save()
            reviews=feedback.objects.filter(broker=broker)
            presentbrokerfeedback=feedback.objects.filter(broker=broker)
            avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
            broker.average_rating=avgrating
            broker.save()
            
            return redirect("app1:customer_home")
    else :
        feedback_form=feedbackform()
        context={
            "feedbackform":feedback_form,
            "unreadmessages":unreadmessages,
            "unreadconnections":unreadconnections,
            "tl":len(unreadconnections)+len(unreadmessages)
        }
        return render(request,"customer/review.html",context)

@login_required
def brokerreviews(request,pk):
    presentbroker=Broker.objects.filter(user__pk=pk).first()
    reviews=feedback.objects.filter(broker=presentbroker)
    presentbrokerfeedback=feedback.objects.filter(broker=presentbroker)
    avgrating=presentbrokerfeedback.aggregate(Avg("rating")).get("rating__avg")
    if avgrating is not None:
        presentbroker.average_rating=avgrating
    else :
        avgrating=0
    presentbroker.save()
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "reviews":reviews,
        "rsize":len(reviews),
        "avgrating":avgrating,
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/review.html",context)

@iscustomer
def customerchat(request,pk):
    presentcustomer=Customer.objects.get(user=request.user)
    presentbroker=Broker.objects.get(pk=pk)
    unreadmessages=Message.objects.filter(customer__user=request.user,is_customerread=False)
    unreadconnections=connection.objects.filter(customer__user=request.user,is_customerread=False)
    if request.method=='POST':
        message=request.POST.get("message")
        if message != "":
            newmessage=Message()
            newmessage.customer=Customer.objects.get(user=request.user)
            newmessage.broker=Broker.objects.get(pk=pk)
            newmessage.message=message
            newmessage.timestamp=timezone.now()
            newmessage.flag=True
            newmessage.is_read=False
            newmessage.save()

    messages=Message.objects.filter(customer=presentcustomer,broker=presentbroker).order_by("-timestamp")[::-1]
    Message.objects.filter(customer=presentcustomer,broker=presentbroker).update(is_customerread=True)
    context={
        "messages":messages,
        "msize":len(messages),
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"customer/chat.html",context)

@isbroker
def brokerchat(request,pk):
    presentcustomer=Customer.objects.get(pk=pk)
    presentbroker=Broker.objects.get(user=request.user)
    if request.method=='POST':
        message=request.POST.get("message")
        if message != "":
            newmessage=Message()
            newmessage.customer=presentcustomer
            newmessage.broker=presentbroker
            newmessage.message=message
            newmessage.timestamp=timezone.now()
            newmessage.flag=False
            newmessage.is_read=False
            newmessage.save()

    messages=Message.objects.filter(customer=presentcustomer,broker=presentbroker).order_by("-timestamp")[::-1]
    Message.objects.filter(customer=presentcustomer,broker=presentbroker).update(is_brokerread=True)
    unreadconnections=connection.objects.filter(broker__user=request.user,is_brokerread=False)
    unreadmessages=Message.objects.filter(broker__user=request.user,is_brokerread=False)
    context={
        "messages":messages,
        "msize":len(messages),
        "unreadmessages":unreadmessages,
        "unreadconnections":unreadconnections,
        "tl":len(unreadconnections)+len(unreadmessages)
    }
    return render(request,"broker/chat.html",context)





