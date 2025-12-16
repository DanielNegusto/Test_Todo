from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, TaskViewSet, TelegramRegisterView

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("telegram/register/", TelegramRegisterView.as_view(), name="telegram-register"),
    path("", include(router.urls)),
]



