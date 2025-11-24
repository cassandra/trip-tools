from django.urls import path

from . import views

urlpatterns = [
    path(
        '',
        views.ImagesHomeView.as_view(),
        name='images_home'
    ),
    path(
        'inspect/<uuid:image_uuid>',
        views.ImageInspectView.as_view(),
        name='images_image_inspect'
    ),
]
