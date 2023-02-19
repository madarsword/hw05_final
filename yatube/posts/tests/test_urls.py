from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    """Создание тестового поста и группы."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='test_user'
        )
        cls.author = User.objects.create_user(
            username='test_author'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание тестовой группы'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый тест тестового поста без группы'
        )

    def setUp(self):
        """Создание клиентов гостя и зарегистрированного пользователя."""
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        cache.clear()

    def test_all_urls(self):
        """Тест статусов для всех видов пользователей.
        Пользователи: гость, авторизованный без постов и автор поста."""
        urls_list = [
            ('/', self.guest_client, HTTPStatus.OK),

            (f'/group/{self.group.slug}/',
             self.guest_client, HTTPStatus.OK),

            (f'/profile/{self.author.username}/',
             self.guest_client, HTTPStatus.OK),

            (f'/posts/{self.post.pk}/',
             self.guest_client, HTTPStatus.OK),

            ('/create/', self.guest_client, HTTPStatus.FOUND),
            ('/create/', self.authorized_client, HTTPStatus.OK),

            (f'/posts/{self.post.pk}/edit/',
             self.guest_client, HTTPStatus.FOUND),
            (f'/posts/{self.post.pk}/edit/',
             self.authorized_client, HTTPStatus.FOUND),
            (f'/posts/{self.post.pk}/edit/',
             self.authorized_author, HTTPStatus.OK),

            ('/unexisting_page/',
             self.guest_client, HTTPStatus.NOT_FOUND),
            ('/unexisting_page/',
             self.authorized_client, HTTPStatus.NOT_FOUND),
            ('/unexisting_page/',
             self.authorized_author, HTTPStatus.NOT_FOUND),
        ]
        for url, client, status_code in urls_list:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, status_code)

    def test_urls_use_correct_templates(self):
        """URL'ы используют корректные шаблоны."""
        templates_pages_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
        }
        for url, template in templates_pages_names.items():
            with self.subTest(url=url):
                response = self.authorized_author.get(url)
                self.assertTemplateUsed(response, template)
