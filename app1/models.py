from django.db import models
from django.contrib.auth.models import AbstractUser
from multiselectfield import MultiSelectField

#Create your models here.


DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
)
lis=[0,1,2,3,4,5]

class User(AbstractUser):
    phone_number=models.PositiveIntegerField(default=0)
    is_customer=models.BooleanField(default=False)
    is_broker=models.BooleanField(default=False)
    picture=models.ImageField(upload_to='profile_pics',blank=True)
    def __str__(self):
        return self.username

class Broker(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    department_name=models.CharField(max_length=30)
    location=models.CharField(max_length=30)
    days=MultiSelectField(choices=DAYS_OF_WEEK,blank=True,default=lis)
    average_rating=models.FloatField(blank=True,default=0,null=True)
    # weekdays = weekday_field.fields.WeekdayField()
    def __str__(self):
        return self.user.__str__()


class Customer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    service_providers=models.ManyToManyField(Broker,through='connection')
    def __str__(self):
        return self.user.__str__()

class connection(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="present_customer")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="present_broker")
    description=models.CharField(max_length=150,blank=True)
    customer_status=models.CharField(max_length=30)
    broker_status=models.CharField(max_length=30)
    created_time=models.DateTimeField()
    modified_time=models.DateTimeField()
    is_brokerread=models.BooleanField(default=False)
    is_customerread=models.BooleanField(default=False)

    def __str__(self):
        return "From "+self.customer.__str__()+" to "+self.broker.__str__()
choices=(
        (1,'worst'),
        (2,'bad'),
        (3,'average'),
        (4,'good'),
        (5,'excellent'),
    )
class feedback(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="feedback_customer")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="feedback_broker")
    description=models.CharField(max_length=150)
    
    rating=models.IntegerField(choices=choices,default=4)
    created_time=models.DateTimeField()
    def __str__(self):
        return "To "+self.broker.__str__()

class Message(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="customer_message")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="broker_message")
    message = models.CharField(max_length=1200)
    timestamp = models.DateTimeField()
    flag=models.BooleanField()
    is_brokerread = models.BooleanField(default=False)
    is_customerread = models.BooleanField(default=False)
    def __str__(self):
        return self.message

    class Meta:
        ordering = ('timestamp',)
