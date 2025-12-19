from django import forms
from .models import Venta, VentaItem

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "fecha", "total", "canal"]


class VentaItemForm(forms.ModelForm):
    class Meta:
        model = VentaItem
        fields = ["producto", "cantidad", "precio_unitario"]
