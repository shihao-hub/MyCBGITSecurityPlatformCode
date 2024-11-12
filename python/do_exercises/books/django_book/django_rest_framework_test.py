from django.db import models
from django.urls import re_path, path, include

import rest_framework

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.routers import DefaultRouter


class Post(models.Model):
    objects = models.Manager()


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    queryset = Post.objects.all()


router = DefaultRouter()
router.register(r"post", PostViewSet, basename="api-post")


urlpatterns = [
    re_path(r"^api/$", include(router.urls, namespace="api"))
]
