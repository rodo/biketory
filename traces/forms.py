from django import forms


class TraceUploadForm(forms.Form):
    gpx_file = forms.FileField(label="GPX file")
