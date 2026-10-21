from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from .forms import ContactMessageForm
from .models import Category, Product


class ProductRegressionTests(TestCase):
    def test_product_detail_is_resolved_by_slug(self):
        category = Category.objects.create(name='Dairy', slug='dairy')
        product = Product.objects.create(
            name='Milk',
            slug='fresh-milk',
            category=category,
            description='Fresh milk',
            price=Decimal('100.00'),
            image='images/products/milk.png',
            stock=5,
        )

        response = self.client.get(f'/products/product/{product.slug}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'], product)

    def test_product_rejects_negative_price_and_protects_its_category(self):
        category = Category.objects.create(name='Dairy', slug='dairy')
        product = Product(
            name='Milk',
            slug='milk',
            category=category,
            description='Fresh milk',
            price=Decimal('-100.00'),
            image='images/products/milk.png',
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

        product.price = Decimal('100.00')
        product.save()
        with self.assertRaises(ProtectedError):
            category.delete()

    def test_contact_honeypot_rejects_automated_submission(self):
        form = ContactMessageForm(data={
            'name': 'Bot',
            'email': 'bot@example.com',
            'subject': 'Spam',
            'message': 'Automated content',
            'website': 'https://spam.example',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('website', form.errors)

    def test_seed_store_bundles_and_copies_images_to_media_storage(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                call_command('seed_store', verbosity=0)

                products = Product.objects.filter(is_active=True)
                self.assertEqual(products.count(), 9)
                for product in products:
                    self.assertTrue(Path(media_root, product.image.name).is_file())
