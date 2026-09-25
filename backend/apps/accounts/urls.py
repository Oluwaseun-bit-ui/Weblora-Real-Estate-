from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

# Minimal token-based auth for the admin API/dashboard. Customers do not
# authenticate for search/browse/lead-submission per the product spec.
urlpatterns = [
    path("token/", obtain_auth_token, name="api-token-auth"),
]
