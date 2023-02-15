import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    """Создаем тестовых юзера, пост и группу."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(
            username='author'
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            group=cls.group,
            author=cls.user,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Создание клиентов гостя и зарегистрированного пользователя."""
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_use_correct_template(self):
        """View-функции используют соответствующие шаблоны."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs=(
                {'slug': f'{self.post.group.slug}'})): 'posts/group_list.html',
            reverse('posts:profile', kwargs=(
                {'username': f'{self.user}'})): 'posts/profile.html',
            reverse('posts:post_detail', kwargs=(
                {'post_id': f'{self.post.id}'})): 'posts/post_detail.html',
            reverse('posts:post_edit', kwargs=(
                {'post_id': f'{self.post.id}'})): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_post(self, response_context):
        if 'page_obj' in response_context:
            post = response_context['page_obj'][0]
        else:
            post = response_context['post']
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.image, self.post.image)

    def post_create_edit(self, response_context):
        form_field = [
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
        ]
        for value, excepted in form_field:
            with self.subTest(value=value):
                form_field = response_context.get('form').fields.get(value)
                self.assertIsInstance(form_field, excepted)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post(response.context)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.check_post(response.context)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.check_post(response.context)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author})
        )
        self.check_post(response.context)
        self.assertEqual(response.context['author'], self.user)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        self.post_create_edit(response.context)

    def test_post_create_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.post_create_edit(response.context)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('about:tech'): 'about/tech.html',
            reverse('about:author'): 'about/author.html',
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_caches(self):
        """Тестирование кэша главной страницы."""
        new_post = Post.objects.create(
            author=self.user,
            text='Пост, который будет удален через 3, 2, 1...',
            group=self.group
        )
        response_1 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_1 = response_1.content
        new_post.delete()
        response_2 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_2 = response_2.content
        self.assertEqual(response_content_1, response_content_2)
        cache.clear()
        response_3 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_3 = response_3.content
        self.assertNotEqual(response_content_2, response_content_3)

    def test_follow(self):
        """Тестирование подписки на автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='John Doe')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author, new_author)
        self.assertEqual(follow.user, PostViewTests.user)

    def test_unfollow(self):
        """Тестирование отписки от автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='John Doe')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow)

    def test_following_posts(self):
        """Тестирование появления поста автора в ленте подписчика."""
        new_user = User.objects.create(username='John Doe')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}
            )
        )
        response_follow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_follow = response_follow.context
        self.check_post(context_follow)

    def test_unfollowing_posts(self):
        """Тестирование отсутствия поста автора у нового пользователя."""
        new_user = User.objects.create(username='John Doe')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        response_unfollow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_unfollow = response_unfollow.context
        self.assertEqual(len(context_unfollow['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)

    AMOUNT_OF_TEST_POSTS = settings.POSTS_PER_PAGE + 3

    def setUp(self):
        self.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовое описание',
            slug='test-slug',
        )
        self.post = Post.objects.bulk_create([
            Post(author=self.author,
                 text=f'Тестовый пост {i}',
                 group=self.group) for i in range(self.AMOUNT_OF_TEST_POSTS)]
        )
        self.page_names_records = {
            'posts:index': '',
            'posts:profile': {'username': self.author.username},
            'posts:group_list': {'slug': self.group.slug},
        }

    def test_first_page_has_ten_posts(self):
        """На первой странице с паджинатором верное количество постов."""
        for page_name, kwarg in self.page_names_records.items():
            with self.subTest(page_name=page_name):
                response = self.client.get(reverse(page_name, kwargs=kwarg))
                self.assertEqual(
                    len(response.context['page_obj']), settings.POSTS_PER_PAGE)

    def test_second_page_has_three_posts(self):
        """На второй странице с паджинатором верное количество постов."""
        POSTS_ON_SECOND_PAGE = (
            self.AMOUNT_OF_TEST_POSTS - settings.POSTS_PER_PAGE
        )
        for page_name, kwarg in self.page_names_records.items():
            with self.subTest(page_name=page_name):
                response = self.client.get(reverse(
                    page_name, kwargs=kwarg) + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_ON_SECOND_PAGE)
