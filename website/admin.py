# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import BlogPost, BlogImage


class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 1


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_name', 'category', 'status', 'is_featured', 'views_count', 'published_at']
    list_filter = ['status', 'is_featured', 'category']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [BlogImageInline]
    date_hierarchy = 'created_at'


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'alt_text', 'position', 'created_at']
    list_filter = ['post']

