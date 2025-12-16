# Documentación de Servicios

## Servicio: Gestión de Turnos

### Endpoint `load_shift` (script_turnos.py)

- **Descripción**: Retorna información completa del estado del turno del guardia, incluyendo la ubicación, la caseta, guardias de apoyo y notas.

- **Método HTTP**: `GET`

**Ejemplo de Request**

```
{
   "location": {
      "name": "Planta Monterrey",
      "area": "Caseta Vigilancia Norte 3",
      "city": null,
      "state": "Nuevo Le\u00f3n",
      "address": "Av. Batall\u00f3n de San Patricio 112, Corporativo Prodesa, 66260 San Pedro Garza Garc\u00eda, N.L."
   },
   "booth_stats": {
      "in_invitees": 11,
      "articulos_concesionados": 12,
      "incidentes_pendites": 13,
      "vehiculos_estacionados": 14,
      "gefetes_pendientes": 15
   },
   "booth_status": {
      "status": "Disponible",
      "guard_on_dutty": "",
      "user_id": "",
      "stated_at": ""
   },
   "support_guards": [
      {
         "_id": "665a536d5d2e1871290e0bf2",
         "folio": "333-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Fernando Sntiba\u00f1ez",
         "user_id": 2,
         "marcada_como": "default",
         "position": "Guardia de Seguridad",
         "picture": {
            "file_name": "police2.png",
            "file_url": "https://f001.backblazeb2.com/file/app-linkaform/public-client-10/119181/663bcbe2274189281359eb70/6658cd60a6b42f73011581c4.png"
         }
      },
      {
         "_id": "665a536df09f6e2b66799e35",
         "folio": "334-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Pedro Cervante",
         "user_id": 1,
         "marcada_como": "normal",
         "position": "Jefe de Seguridad",
         "picture": {
            "file_name": "police.png",
            "file_url": "https://f001.backblazeb2.com/file/app-linkaform/public-client-10/119181/663bcbe2274189281359eb70/6658cc59fabe5360581c0bec.png"
         }
      },
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Empleado Seguridad",
         "user_id": 10,
         "marcada_como": "default",
         "position": "Guardia de Seguridad",
         "picture": {
            "file_name": "avatar2.png",
            "file_url": "https://f001.backblazeb2.com/file/app-linkaform/public-client-10/119181/663bcbe2274189281359eb70/667afc7956232709f0a3f172.png"
         }
      }
   ],
   "guard": {
      "_id": "6679991d894980450057d63e",
      "folio": "349-10",
      "created_at": "2024-06-24",
      "area": "Caseta Vigilancia Norte 3",
      "location": "Planta Monterrey",
      "employee": "Empleado Seguridad",
      "user_id": 10,
      "marcada_como": "default",
      "position": "Guardia de Seguridad",
      "picture": {
         "file_name": "avatar2.png",
         "file_url": "https://f001.backblazeb2.com/file/app-linkaform/public-client-10/119181/663bcbe2274189281359eb70/667afc7956232709f0a3f172.png"
      },
      "turn_start_datetime": "2024-07-25 18:18:29",
      "status_turn": "Turno Cerrado"
   },
   "notes": [],
   "user_booths": [
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Caseta Vigilancia Poniente 7",
         "location": "Planta Monterrey",
         "employee": "Empleado Seguridad",
         "marcada_como": "normal"
      },
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Caseta Vigilancia Sur 5",
         "location": "Planta Monterrey",
         "employee": "Empleado Seguridad",
         "marcada_como": "normal"
      },
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Almacen de equipos industriales",
         "location": "Planta Durango",
         "employee": "Empleado Seguridad",
         "marcada_como": "normal"
      }
   ]
}
```

### Endpoint `guardias_de_apoyo` / `get_boot_guards` ó `list_chiken_guards`

- **Descripción**: Retorna una lista de guardias de apoyo disponibles.

- **Método HTTP**: `GET`

**Ejemplo de Request**

```
{
   "guardia": [
      {
         "_id": "665a536d5d2e1871290e0bf2",
         "folio": "333-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Fernando Sntiba\u00f1ez",
         "user_id": 2,
         "marcada_como": "default",
         "position": "Guardia de Seguridad"
      },
      {
         "_id": "665a536df09f6e2b66799e35",
         "folio": "334-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Pedro Cervante",
         "user_id": 1,
         "marcada_como": "normal",
         "position": "Jefe de Seguridad"
      },
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Empleado Seguridad",
         "user_id": 10,
         "marcada_como": "default",
         "position": "Guardia de Seguridad"
      }
   ],
   "guardia_de_apoyo": [
      {
         "_id": "665a536d5d2e1871290e0bf2",
         "folio": "333-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Fernando Sntiba\u00f1ez",
         "user_id": 2,
         "marcada_como": "default",
         "position": "Guardia de Seguridad"
      },
      {
         "_id": "665a536df09f6e2b66799e35",
         "folio": "334-10",
         "created_at": "2024-05-31",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Pedro Cervante",
         "user_id": 1,
         "marcada_como": "normal",
         "position": "Jefe de Seguridad"
      },
      {
         "_id": "6679991d894980450057d63e",
         "folio": "349-10",
         "created_at": "2024-06-24",
         "area": "Caseta Vigilancia Norte 3",
         "location": "Planta Monterrey",
         "employee": "Empleado Seguridad",
         "user_id": 10,
         "marcada_como": "default",
         "position": "Guardia de Seguridad"
      }
   ]
}
```

