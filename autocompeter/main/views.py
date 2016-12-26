from django.shortcuts import render
# from django.contrib import messages


def home(request):
    context = {}
    return render(request, 'main/home.html', context)
