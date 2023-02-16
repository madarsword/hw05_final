from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    """Создаем тестовый пост и группу."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text=('Тестовый пост для проверки, '
                  'больше ли пятнадцати символов строка'),
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            slug='Тестовый слаг группы',
            description='Тестовое описание группы'
        )

    def test_group_models_have_correct_object_names(self):
        """Проверяем, что у групп корректно работает __str__."""
        self.assertEqual(str(PostModelTest.group), PostModelTest.group.title)

    def test_post_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        self.assertEqual(str(self.post), self.post.text[:15])

    def test_models_have_verbose_name(self):
        """verbose_name совпадает с ожидаемым."""
        post = PostModelTest.post
        field_verboses = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.post._meta.get_field(field).verbose_name, expected_value
                )

    def test_models_have_help_text(self):
        """help_text совпадает с ожидаемым."""
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост'
        }
        for field, expected_value in field_help_texts.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.post._meta.get_field(field).help_text, expected_value
                )
