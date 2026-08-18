from diezapp.features.google_drive.domain.repositories import DriveAccountRepository


class LinkAccountService:
    def __init__(
        self, account_repository: DriveAccountRepository, max_accounts: int = 2
    ):
        self._account_repository = account_repository
        self._max_accounts = max_accounts

    def can_add_account(self) -> bool:
        return self._account_repository.count() < self._max_accounts

    def add_account(
        self,
        email: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> str:
        if not self.can_add_account():
            raise ValueError(f"Ya hay {self._max_accounts} cuentas vinculadas")
        return self._account_repository.add(
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    def complete_link(
        self,
        query_params: dict,
        pending_state: str | None,
        is_web_runtime: bool,
        callback_done: bool = False,
    ) -> dict:
        if callback_done:
            return {"ok": False, "message": "La vinculación ya fue procesada"}

        returned_state = query_params.get("app_state")
        if not is_web_runtime and (
            not pending_state or returned_state != pending_state
        ):
            return {"ok": False, "message": "No se pudo completar la vinculación"}

        if query_params.get("error"):
            return {"ok": False, "message": "Vinculación cancelada"}

        access_token = query_params.get("access_token")
        email = query_params.get("email")
        if not access_token or not email:
            return {
                "ok": False,
                "message": "El callback no recibió los datos de Google",
            }

        try:
            expires_in = int(query_params.get("expires_in", 3600))
        except ValueError:
            expires_in = 3600

        try:
            self.add_account(
                email=email,
                access_token=access_token,
                refresh_token=query_params.get("refresh_token", ""),
                expires_in=expires_in,
            )
        except ValueError as error:
            return {"ok": False, "message": str(error)}

        return {"ok": True, "message": f"Cuenta {email} vinculada"}
