from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_posts(posts=None, only_published=True):
    """Добавляет к постам число комментариев и связанные объекты.

    При only_published=True отбирает только опубликованные посты
    с опубликованной категорией и датой публикации не позже текущей.
    """
    if posts is None:
        posts = Post.objects.all()
    posts = posts.select_related('author', 'category', 'location')
    if only_published:
        posts = posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
    return posts.annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def paginate(request, posts):
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


def index(request):
    page_obj = paginate(request, get_posts())
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    page_obj = paginate(request, get_posts(category.posts.all()))
    context = {'category': category, 'page_obj': page_obj}
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        # Чужие посты видны, только если они опубликованы.
        post = get_object_or_404(get_posts(), pk=post_id)
    context = {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    }
    return render(request, 'blog/detail.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    # Автор видит все свои посты, включая отложенные и снятые с публикации.
    posts = get_posts(
        author.posts.all(), only_published=request.user != author
    )
    context = {'profile': author, 'page_obj': paginate(request, posts)}
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', request.user.username)
    context = {'form': PostForm(instance=post)}
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(get_posts(), pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user
    )
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'form': form, 'comment': comment}
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user
    )
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
