{{/* Common labels shared across all Aura resources */}}
{{- define "aura.labels" -}}
app.kubernetes.io/part-of: aura
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
