from django.urls import path

from . import views

urlpatterns = [
    path(
        r'',
        views.ImagesHomeView.as_view(),
        name='images_home'
    ),
    path(
        r'inspect/<uuid:image_uuid>',
        views.ImageInspectView.as_view(),
        name='images_image_inspect'
    ),
]
