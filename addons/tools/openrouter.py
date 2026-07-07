# -*- coding: utf-8 -*-
"""
addons/tools/openrouter.py

Cliente OpenRouter para lkf_addons (lkf-sanic-apps).

El linkaform_api instalado en este proyecto (3.0) todavía no incluye la
integración de OpenRouter que sí existe en linkaform_api más reciente, por lo
que se porta aquí de forma autocontenida (sin depender de LKFBaseObject) y se
instancia manualmente en addons/base/app.py (Base.__init__) si el usuario
configuró OPENROUTER_API_KEY.

Uso básico desde cualquier módulo de lkf_addons:

    # Si el usuario configuró OPENROUTER_API_KEY, self.ai estará disponible
    if self.ai:
        result = self.ai.ocr_id("https://s3.../ine.jpg")
        result = self.ai.chat("¿Cuántos registros hay del form 345?")
        result = self.ai.chat("resume esto", image_url="https://...")
"""

import json
import base64
import requests
from pathlib import Path


# Modelo por default — puede sobreescribirse en account_settings con OPENROUTER_MODEL
DEFAULT_MODEL = 'google/gemini-2.5-flash'

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


class OpenRouter:
    """
    Cliente OpenRouter para LinkaForm.

    Expone métodos de alto nivel listos para usar en lkf_addons:
        - chat()       → conversación general con o sin imagen
        - ocr_id()     → extrae datos de una identificación
        - ocr()        → OCR genérico para cualquier imagen
        - ocr_general()→ OCR genérico con system/prompt custom

    Y métodos de bajo nivel para casos custom:
        - post()       → llamada directa a la API con messages completos
    """

    def __init__(self, config: dict):
        """
        Args:
            config: settings.config de LinkaForm.
                    Requiere: OPENROUTER_API_KEY
                    Opcional: OPENROUTER_MODEL, ACCOUNT_ID, USER_ID
        """
        self.api_key   = config.get('OPENROUTER_API_KEY', '')
        self.model     = config.get('OPENROUTER_MODEL', DEFAULT_MODEL)
        self.account_id = config.get('ACCOUNT_ID', '')
        self.user_id    = config.get('USER_ID', '')

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY no está configurada en account_settings.py"
            )

        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type':  'application/json',
            'HTTP-Referer':  'https://web.clave10.com',
            'X-Title':       'Clave10',
        }

    # ──────────────────────────────────────────────────────────
    # MÉTODOS PÚBLICOS DE ALTO NIVEL
    # ──────────────────────────────────────────────────────────

    def chat(self, prompt: str, image_url = None,
             system: str = None, model: str = None,
             max_tokens: int = 1000, temperature: float = 0) -> str:
        """
        Conversación general con el LLM, con o sin imagen.

        Args:
            prompt:      El mensaje del usuario.
            image_url:   URL o ruta local de imagen (opcional).
            system:      System prompt custom (opcional).
            model:       Modelo a usar (opcional, usa el default del config).
            max_tokens:  Máximo de tokens en la respuesta.
            temperature: 0 = determinista, 1 = creativo.

        Returns:
            dict con la respuesta completa de OpenRouter.

        Ejemplo:
            texto = self.ai.chat("Resume este documento", image_url="https://...")
            texto = self.ai.chat("¿Qué es LinkaForm?")
        """
        messages = []

        if system:
            messages.append({'role': 'system', 'content': system})

        user_content = self._build_user_content(prompt, image_url)
        messages.append({'role': 'user', 'content': user_content})

        data = self.post(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return data

    def ocr_id(self, image_source: list, model: str = 'google/gemini-2.5-flash-lite', name: str = None) -> dict:
        """
        Extrae datos de todas las identificaciones visibles en la imagen
        (INE, pasaporte, licencia, credencial escolar, etc.) y las retorna
        como lista de dicts, una por identificación encontrada.

        Args:
            image_source: URL remota o ruta local de la imagen.
            model:        Modelo a usar (opcional).
            name:         Si se indica, valida que al menos una ID pertenezca a esa persona.

        Ejemplo:
            datos = self.ai.ocr_id("https://s3.amazonaws.com/.../ids.jpg")
            datos = self.ai.ocr_id("/tmp/identificaciones.png")
        """
        self.headers['X-Title'] = 'Clave10: OCR ID'
        system = (
            "Eres un OCR especializado en identificaciones oficiales. "
            "Responde ÚNICAMENTE con JSON válido, sin texto adicional y sin bloques de código. "
            "Usa null para campos ilegibles o ausentes."
        )
        prompt = (
            "Analiza la imagen y detecta TODAS las identificaciones presentes "
            "(puede haber una o varias).\n"
        )
        if name:
            prompt += (
                f"Valida que al menos una identificación pertenezca a '{name}'. "
                f"Si ninguna pertenece a '{name}', incluye en ese objeto: "
                f'"status": "La identificacion no pertenece a {name}", "status_code": 406\n'
            )

        prompt += """Para CADA identificación encontrada extrae sus datos y devuelve un array JSON
            donde cada elemento corresponde a una identificación con estos campos:
            - tipo_documento   (IMPORTANTE: indica exactamente el tipo: INE, Pasaporte, Licencia de conducir,
                                Credencial escolar, etc.)
            - nombre
            - apellido_paterno
            - apellido_materno
            - fecha_nacimiento  (formato YYYY-MM-DD si es posible)
            - sexo
            - curp
            - rfc
            - direccion: {
                calle,
                colonia,
                municipio,
                estado,
                cp
            }
            - fecha_vigencia
            - fecha_expedicion
            - numero_documento
            - nacionalidad
            - status_vigencia   (\"vigente\" o \"vencida\" según la fecha de vigencia)

            Si solo hay una identificación devuelve igualmente un array con un solo elemento.
            Responde SOLO con el array JSON, sin explicaciones."""

        raw = self.chat(
            prompt=prompt,
            image_url=image_source,
            system=system,
            model=model,
            max_tokens=1500,
            temperature=0,
        )
        return self._parse_json(raw)

    def ocr(self, image_source: list, fields: list = None,
            extra_instructions: str = None, model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        OCR genérico para cualquier imagen.

        Args:
            image_source:       URL remota o ruta local.
            fields:              Lista de campos a extraer (opcional).
                                 Si no se especifica, extrae todo lo visible.
            extra_instructions: Instrucciones adicionales al modelo (opcional).
            model:              Modelo a usar (opcional).

        Ejemplo:
            datos = self.ai.ocr(
                "https://.../factura.jpg",
                fields=["numero_factura", "total", "fecha", "rfc_emisor"],
            )
        """
        self.headers['X-Title'] = 'Clave10: OCR'

        system = (
            "Eres un OCR. Analiza la imagen y extrae los campos solicitados. "
            "Responde ÚNICAMENTE con JSON válido, sin texto adicional. "
            "Usa null si un campo no está visible."
        )

        if fields:
            fields_str = ", ".join(fields)
            prompt = f"Extrae los siguientes campos: {fields_str}."
        else:
            prompt = "Extrae todos los campos de texto visibles en la imagen."

        if extra_instructions:
            prompt += f" {extra_instructions}"

        prompt += " Responde SOLO el JSON."

        raw = self.chat(
            prompt=prompt,
            image_url=image_source,
            system=system,
            model=model,
            max_tokens=800,
            temperature=0,
        )
        return self._parse_json(raw)

    def ocr_general(self, image_source: list, system: str, prompt: str,
            model: str = None, agent: str = 'Clave10', max_tokens: int = 600):
        """
        OCR genérico con system/prompt custom, retorna el dict crudo de
        OpenRouter (choices/usage) con el content ya parseado a JSON.

        Args:
            image_source: URL remota, ruta local, o lista de imágenes.
            system:       System prompt custom.
            prompt:       Prompt custom.
            model:        Modelo a usar (opcional).
        """
        self.headers['X-Title'] = agent

        raw = self.chat(
            prompt=prompt,
            image_url=image_source,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=0,
        )
        return self._parse_json(raw)

    # ──────────────────────────────────────────────────────────
    # MÉTODO DE BAJO NIVEL
    # ──────────────────────────────────────────────────────────

    def post(self, messages: list, model: str = None,
                   max_tokens: int = 1000, temperature: float = 0,
                   tools: list = None) -> dict:
        """
        Llamada directa a la API de OpenRouter.
        Útil para casos avanzados donde necesitas controlar
        el historial de mensajes completo o usar tools.

        Returns:
            dict completo del response de OpenRouter (choices, usage, etc.)
        """

        self.headers['X-Title'] = 'Clave10: Direct'

        payload = {
            'model':       model or self.model,
            'messages':    messages,
            'max_tokens':  max_tokens,
            'temperature': temperature,
        }
        if tools:
            payload['tools'] = tools
        resp = requests.post(
            OPENROUTER_URL,
            headers=self.headers,
            json=payload,
            timeout=60,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"OpenRouter [{resp.status_code}]: {resp.text}"
            )

        return resp.json()

    # ──────────────────────────────────────────────────────────
    # HELPERS PRIVADOS
    # ──────────────────────────────────────────────────────────

    def _build_image_url(self, image_source: str) -> str:
        """
        Prepara la URL de la imagen para el payload.
        - data: URL  → ya está en base64, se devuelve tal cual
        - URL remota → se devuelve tal cual
        - Archivo local → convierte a base64
        """
        if image_source.startswith('data:'):
            return image_source

        if image_source.startswith('http://') or image_source.startswith('https://'):
            return image_source

        # Archivo local → base64
        ext = Path(image_source).suffix.lower()
        media_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png',  '.gif':  'image/gif',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf',
        }
        media_type = media_types.get(ext, 'image/jpeg')
        with open(image_source, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f'data:{media_type};base64,{b64}'

    def _build_user_content(self, prompt: str, image_url=None):
        """
        Construye el content del mensaje user.

        - Sin imagen        → string simple
        - Una imagen (str)  → lista [image, text]
        - Varias imágenes   → lista [image1, image2, ..., text]
        """
        if not image_url:
            return prompt

        # Normalizar siempre a lista
        if isinstance(image_url, str):
            images = [image_url]
        else:
            images = list(image_url)

        # Construir content: primero todas las imágenes, luego el texto
        content = [
            {
                'type':      'image_url',
                'image_url': {'url': self._build_image_url(img)},
            }
            for img in images
        ]
        content.append({'type': 'text', 'text': prompt})

        return content

    def _parse_json(self, raw_text: dict) -> dict:
        """
        Parsea la respuesta del modelo como JSON.
        Limpia bloques de código markdown si los hay.
        Detecta respuestas truncadas por límite de tokens.
        """
        res = ""
        if raw_text.get('choices'):
            if isinstance(raw_text['choices'], list) and len(raw_text['choices']) > 0:
                choice = raw_text['choices'][0]

                # ── Detectar truncamiento ANTES de parsear ────────────
                finish_reason = choice.get('finish_reason')
                native_finish = choice.get('native_finish_reason')
                if finish_reason == 'length' or native_finish == 'MAX_TOKENS':
                    raise RuntimeError(
                        f"Respuesta truncada por límite de tokens (finish_reason='{finish_reason}'). "
                        f"Tokens usados: {raw_text.get('usage', {}).get('completion_tokens')}. "
                        f"Aumenta max_tokens en la llamada al modelo."
                    )

                if choice.get('message', {}).get('content'):
                    res = choice['message']['content'].strip()

        text = res.strip()

        # ── Limpiar bloques markdown ```json ... ``` ──────────────────
        if text.startswith('```'):
            lines = text.split('\n')
            # Remover primera línea (```json) y última (```)
            text = '\n'.join(lines[1:-1]).strip()

        # ── Parsear JSON ──────────────────────────────────────────────
        try:
            parsed = json.loads(text)
            raw_text['choices'][0]['message']['content'] = parsed
            return raw_text
        except json.JSONDecodeError as e:
            raise ValueError(
                f"El modelo no devolvió JSON válido: {e}\n"
                f"Fragmento problemático: ...{text[max(0, e.pos-50):e.pos+50]}..."
            )
