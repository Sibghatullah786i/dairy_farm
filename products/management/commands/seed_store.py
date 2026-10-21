from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from products.models import Category, Product


STARTER_PRODUCTS = [
    {
        'category_name': 'Fresh Dairy',
        'category_slug': 'fresh-dairy',
        'name': 'Fresh Cow Milk',
        'slug': 'fresh-cow-milk',
        'description': 'Fresh milk delivered directly from the farm.',
        'price': '250.00',
        'image': 'images/products/cow-milk.png',
    },
    {
        'category_name': 'Milk Products',
        'category_slug': 'milk-products',
        'name': 'Chocolate Milk Shake',
        'slug': 'chocolate-milk-shake',
        'description': 'A rich and refreshing chocolate milk shake.',
        'price': '180.00',
        'image': 'images/products/milk-shake-chocolate.png',
    },
    {
        'category_name': 'Yogurt Products',
        'category_slug': 'yogurt-products',
        'name': 'Sweet Lassi',
        'slug': 'sweet-lassi',
        'description': 'Traditional sweet lassi made with fresh dairy.',
        'price': '120.00',
        'image': 'images/products/sweet-lassi.png',
    },
    {
        'category_name': 'Cheese Products',
        'category_slug': 'cheese-products',
        'name': 'Paneer Lite',
        'slug': 'paneer-lite',
        'description': 'Soft paneer made from fresh milk.',
        'price': '450.00',
        'image': 'images/products/paneer-lite.png',
    },
    {
        'category_name': 'Butter & Spreads',
        'category_slug': 'butter-spreads',
        'name': 'Cow Ghee',
        'slug': 'cow-ghee',
        'description': 'Traditional pure cow ghee.',
        'price': '1500.00',
        'image': 'images/products/cow-ghee.png',
    },
    {
        'category_name': 'Cream Products',
        'category_slug': 'cream-products',
        'name': 'Full Cream Milk',
        'slug': 'full-cream-milk',
        'description': 'Creamy full-fat milk for everyday use.',
        'price': '280.00',
        'image': 'images/products/fullcream-milk.png',
    },
    {
        'category_name': 'Traditional Dairy',
        'category_slug': 'traditional-dairy',
        'name': 'Farm Fresh Dairy',
        'slug': 'farm-fresh-dairy',
        'description': 'A selection of traditional farm dairy products.',
        'price': '300.00',
        'image': 'images/products/milk.jpg',
    },
    {
        'category_name': 'Frozen Dairy',
        'category_slug': 'frozen-dairy',
        'name': 'Kulfi',
        'slug': 'kulfi',
        'description': 'Traditional frozen dairy dessert.',
        'price': '150.00',
        'image': 'images/products/kulfi.png',
    },
    {
        'category_name': 'Dairy Desserts',
        'category_slug': 'dairy-desserts',
        'name': 'Sabja Dessert',
        'slug': 'sabja-dessert',
        'description': 'A refreshing dairy dessert with sabja.',
        'price': '200.00',
        'image': 'images/products/sabja.png',
    },
]


class Command(BaseCommand):
    help = 'Create or update the starter dairy categories and products.'

    def handle(self, *args, **options):
        for entry in STARTER_PRODUCTS:
            source_path = (
                Path(settings.BASE_DIR)
                / 'products'
                / 'seed_images'
                / Path(entry['image']).name
            )
            if not source_path.is_file():
                raise CommandError(f'Seed image does not exist: {source_path}')
            if not default_storage.exists(entry['image']):
                with source_path.open('rb') as source_file:
                    default_storage.save(entry['image'], File(source_file))

            category, _ = Category.objects.update_or_create(
                slug=entry['category_slug'],
                defaults={'name': entry['category_name']},
            )
            product, created = Product.objects.get_or_create(
                slug=entry['slug'],
                defaults={
                    'name': entry['name'],
                    'category': category,
                    'description': entry['description'],
                    'price': entry['price'],
                    'image': entry['image'],
                    'stock': 20,
                    'is_active': True,
                },
            )
            if not created:
                product.name = entry['name']
                product.category = category
                product.description = entry['description']
                product.price = entry['price']
                product.image = entry['image']
                product.is_active = True
                product.save()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(STARTER_PRODUCTS)} categories and products.'
        ))
