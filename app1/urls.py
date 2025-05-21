from django.urls import path, include # Added include
from app1.views import (homepage,customerdetail,customerlogin,customersignup,customerlogout,customerorders,customerreview,customerchat,
                        customerprofile,customeracceptedorders,customercompletedorders,customerpendingorders,customerrejectedorders,
                        report_dispute,
                        brokerdetail,brokerlogin,brokersignup,brokerlogout,brokerrequests,brokerprofile,brokerreviews,brokerchat,
                        brokeracceptedrequests,brokercompletedrequests,brokerpendingrequests,brokerrejectedrequests,
                        # Blog views
                        BlogPostListView, BlogPostDetailView, BlogPostCreateView, BlogPostUpdateView,
                        # Payment views
                        create_checkout_session, payment_success, payment_cancel)

app_name='app1'

urlpatterns = [
    path('',homepage.as_view(),name="homepage"),
    path('customer/login/',customerlogin,name="customer_login"),
    path('customer/logout/',customerlogout,name="customer_logout"),
    path('customer/signup/',customersignup,name="customer_signup"),
    path('customer/detail/',customerdetail,name="customer_home"),
    path('customer/orders/',customerorders,name="customer_orders"),
    path('customer/pendingorders/',customerpendingorders,name="customer_pendingorders"),
    path('customer/acceptedorders/',customeracceptedorders,name="customer_acceptedorders"),
    path('customer/completedorders/',customercompletedorders,name="customer_completedorders"),
    path('customer/rejectedorders/',customerrejectedorders,name="customer_rejectedorders"),
    path('customer/review/<int:pk>/',customerreview,name="customer_review"),
    path('customer/chat/<int:pk>/',customerchat,name="customer_chat"),
    path('customer/profile/',customerprofile,name="customer_profile"),
    path('customer/report_dispute/<int:connection_id>/', report_dispute, name='report_dispute'),
    # Payment URLs
    path('customer/create-checkout-session/<int:connection_id>/', create_checkout_session, name='create_checkout_session'),
    path('customer/payment-success/', payment_success, name='payment_success'),
    path('customer/payment-cancel/', payment_cancel, name='payment_cancel'),
    path('mediator/login/',brokerlogin,name="broker_login"),
    path('mediator/logout/',brokerlogout,name="broker_logout"),
    path('mediator/signup/',brokersignup,name="broker_signup"),
    path('mediator/detail/',brokerdetail,name="broker_home"),
    path('mediator/requests/',brokerrequests,name="broker_requests"),
    path('mediator/completedrequests/',brokercompletedrequests,name="broker_completedrequests"),
    path('mediator/pendingrequests/',brokerpendingrequests,name="broker_pendingrequests"),
    path('mediator/acceptedrequests/',brokeracceptedrequests,name="broker_acceptedrequests"),
    path('mediator/rejectedrequests/',brokerrejectedrequests,name="broker_rejectedrequests"),
    path('mediator/profile/',brokerprofile,name="broker_profile"),
    path('mediator/reviews/<int:pk>',brokerreviews,name="broker_reviews"),
    path('mediator/chat/<int:pk>/',brokerchat,name="broker_chat"),

    # Blog URLs
    path('blog/', include([
        path('', BlogPostListView.as_view(), name='blog_post_list'),
        path('new/', BlogPostCreateView.as_view(), name='blog_post_create'),
        path('<slug:slug>/', BlogPostDetailView.as_view(), name='blog_post_detail'),
        path('<slug:slug>/edit/', BlogPostUpdateView.as_view(), name='blog_post_edit'),
    ])),
]

