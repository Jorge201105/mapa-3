from django import forms
from .models import Cliente, Venta


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "telefono", "email", "comuna", "direccion"]

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()

        if not telefono:
            return telefono

        qs = Cliente.objects.filter(telefono=telefono)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un cliente con ese teléfono.")

        return telefono


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = [
            "cliente",
            "tipo_documento",
            "numero_documento",
            "canal",
            "total",
        ]

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_documento")
        numero = (cleaned_data.get("numero_documento") or "").strip()

        if tipo != Venta.TipoDocumento.SIN_DOC and not numero:
            self.add_error(
                "numero_documento",
                "Debes ingresar el número de la factura o boleta."
            )

        return cleaned_data
