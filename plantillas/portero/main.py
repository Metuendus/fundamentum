# Portero de Firebase Auth de una app (plantilla de fundamentum-acceso).
# Copiar a `firebase/portero/` de la app, cambiar APP y desplegar con
# `firebase deploy --only functions:portero_crear,functions:portero_entrar`.
# Requisitos: el proyecto en Identity Platform y la cuenta de la función con roles/datastore.viewer
# en el proyecto central (josecarloscorona-web).
from firebase_functions import identity_fn, options
from fundamentum_acceso import LectorFirestore, crear_portero

APP = "iterum"  # iterum | domi | vocatio

options.set_global_options(region="us-central1", max_instances=5)
portero = crear_portero(APP, LectorFirestore.central)


@identity_fn.before_user_created()
def portero_crear(evento: identity_fn.AuthBlockingEvent) -> None:
    portero(evento)


@identity_fn.before_user_signed_in()
def portero_entrar(evento: identity_fn.AuthBlockingEvent) -> None:
    portero(evento)
