from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "telefono", "email", "comuna", "direccion"]

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()

        # Si está vacío, no validamos duplicados
        if not telefono:
            return telefono

        # Evitar duplicado por teléfono, pero permitiendo editar el mismo registro
        qs = Cliente.objects.filter(telefono=telefono)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un cliente con ese teléfono.")

        return telefono
