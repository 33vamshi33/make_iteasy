from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from app1.models import User,Customer,Broker,connection,feedback

class userform(UserCreationForm):
    class Meta():
        model=User
        fields=('username','email',"phone_number")

class loginform(forms.ModelForm):
    class Meta():
        fields=('username','password')
class brokerform(forms.ModelForm):

    class Meta():
        model=Broker
        fields=('department_name','location','days')

class searchform(forms.ModelForm):
    
    class Meta():
        model=Broker
        fields=('department_name','location','days')


class userprofileform(forms.ModelForm):
    class Meta():
        model=User
        fields=('picture',)

class feedbackform(forms.ModelForm):
    class Meta():
        model=feedback
        fields=("rating","description")




