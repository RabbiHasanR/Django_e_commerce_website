from django.conf import settings
from django.shortcuts import reverse
from django.db import models


CATEGORY_CHOICES=(
    ('S','Shirt'),
    ('SW','Sport wear'),
    ('OW','Out wear')
)

LABEL_CHOICES=(
    ('P','primary'),
    ('S','secondary'),
    ('D','danger')
)

# Create your models here.
class Item(models.Model):
    title=models.CharField(max_length=100)
    price=models.FloatField()
    discount_price = models.FloatField(blank=True,null=True)
    category=models.CharField(choices=CATEGORY_CHOICES,max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug=models.SlugField()
    discription=models.TextField()


    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('core:product-detail',kwargs={
            'slug':self.slug
        })

    def get_add_to_cart_url(self):
        return reverse('core:add-to-cart', kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse('core:remove-from-cart', kwargs={
            'slug': self.slug
        })

class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    ordered = models.BooleanField(default=False)
    def __str__(self):
        return f'{self.quantity} of {self.item.title}'

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_item_discount_price(self):
        return self.quantity * self.item.discount_price
    def get_amount_saved(self):
        return self.get_total_item_price()-self.get_total_item_discount_price()
    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_item_discount_price()
        return self.get_total_item_price()

class Order(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    item=models.ManyToManyField(OrderItem)
    start_date=models.DateTimeField(auto_now_add=True)
    ordered_date=models.DateTimeField()
    ordered=models.BooleanField(default=False)
    def __str__(self):
        return self.user.username

    def get_total_order_price(self):
        total=0
        for order_item in self.item.all():
            total+=order_item.get_final_price()
        return total

