from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.paginator import Paginator
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import User, Post, Follow, Like

def index(request):
    all_posts = Post.objects.all().order_by("id").reverse()

    # Pagination
    paginator = Paginator(all_posts, 10)
    page_number = request.GET.get("page")
    posts_of_page = paginator.get_page(page_number)

    # Liked posts
    liked_posts = []
    if request.user.is_authenticated:
        liked_posts = list(request.user.liked_posts.values_list('id', flat=True))
               
    return render(request, "network/index.html", {
        "all_posts": all_posts,
        "posts_of_page": posts_of_page,
        "liked_posts": liked_posts
    })

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")

def new_post(request):
    if request.method == "POST":
        user = User.objects.get(pk=request.user.id)
        content = request.POST["content"]
        post = Post(user=user, content=content)
        post.save()
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/new_post.html")

def profile(request, user_id):
    user = User.objects.get(pk=user_id)
    all_posts = Post.objects.filter(user=user).order_by("id").reverse()

    followings = Follow.objects.filter(follower=user)
    followers = Follow.objects.filter(following=user)

    try:
        check_follow = followers.filter(follower=request.user)
        if check_follow.exists():
            is_following = True
        else:
            is_following = False
    except:
        is_following = False

    paginator = Paginator(all_posts, 10)
    page_number = request.GET.get("page")
    posts_of_page = paginator.get_page(page_number)

    return render(request, "network/profile.html", {
        "username": user.username,
        "all_posts": all_posts,
        "posts_of_page": posts_of_page,
        "followings": followings,
        "followers": followers,
        "is_following": is_following,
        "user_profile": user
    })

@csrf_exempt
def follow(request):
    if request.method == "POST":
        data = json.loads(request.body)
        userfollow = data.get("userfollow")
        user = request.user
        userfollowData = User.objects.get(username=userfollow)
        follow, created = Follow.objects.get_or_create(follower=user, following=userfollowData)
        if created:
            return JsonResponse({"message": "Followed successfully."}, status=201)
        else:
            return JsonResponse({"message": "Already following."}, status=200)

@csrf_exempt
def unfollow(request):
    if request.method == "POST":
        data = json.loads(request.body)
        userfollow = data.get("userfollow")
        user = request.user
        userfollowData = User.objects.get(username=userfollow)
        try:
            follow = Follow.objects.get(follower=user, following=userfollowData)
            follow.delete()
            return JsonResponse({"message": "Unfollowed successfully."}, status=200)
        except Follow.DoesNotExist:
            return JsonResponse({"message": "You are not following this user."}, status=404)

def following(request):
    user = User.objects.get(pk=request.user.id)
    followings = Follow.objects.filter(follower=user)
    followings_posts = Post.objects.filter(user__in=followings.values('following')).order_by('-timestamp')

    liked_posts = list(user.liked_posts.values_list('id', flat=True))

    # Pagination
    paginator = Paginator(followings_posts, 10)
    page_number = request.GET.get("page")
    posts_of_page = paginator.get_page(page_number)

    return render(request, "network/following.html", {
        "posts_of_page": posts_of_page,
        "liked_posts": liked_posts
    })

def edit(request, post_id):
    if request.method == "POST":
        data = json.loads(request.body)
        edit_content = Post.objects.get(pk=post_id)
        edit_content.content = data["content"]
        edit_content.save()
        return JsonResponse({"message": "Post edited successfully.", "data": data["content"]})


def add_like(request, post_id):
    post = Post.objects.get(pk=post_id)
    user = User.objects.get(pk=request.user.id)
    like, created = Like.objects.get_or_create(user=user, post=post)
    if created:
        post.likes.add(user)
    return JsonResponse({"message": "Liked!", "likes_count": post.likes.count()})


def remove_like(request, post_id):
    post = Post.objects.get(pk=post_id)
    user = User.objects.get(pk=request.user.id)
    like = Like.objects.filter(user=user, post=post).first()
    if like:
        post.likes.remove(user)
        like.delete()
    return JsonResponse({"message": "Unliked!", "likes_count": post.likes.count()})
