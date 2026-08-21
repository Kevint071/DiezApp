from diezapp.features.google_drive.domain.repositories import DriveAccountRepository


class LinkAccountService:
    def __init__(
        self, account_repository: DriveAccountRepository, max_accounts: int = 2
    ):
        self._account_repository = account_repository
        self._max_accounts = max_accounts

    def can_add_account(self) -> bool:
        return self._account_repository.count() < self._max_accounts

    def list_accounts(self):
        return self._account_repository.list()

    def remove_account(self, account_id: str) -> None:
        self._account_repository.remove(account_id)

    def set_account_folder(
        self, account_id: str, folder_id: str | None, folder_name: str | None
    ) -> None:
        self._account_repository.set_folder(account_id, folder_id, folder_name)

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

    def update_account_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None:
        self._account_repository.update_tokens(
            account_id, access_token, refresh_token, expires_in
        )

    def complete_link(
        self,
        query_params: dict,
        pending_state: str | None,
        is_web_runtime: bool,
        callback_done: bool = False,
        account_id: str | None = None,
    ) -> dict:
        if callback_done:
            print("[DEBUG-AUTH] rejected: callback_done already True")  # noqa: T201
            return {"ok": False, "message": "La vinculación ya fue procesada"}

        returned_state = query_params.get("app_state")
        if not is_web_runtime and (
            not pending_state or returned_state != pending_state
        ):
            print(  # noqa: T201
                f"[DEBUG-AUTH] rejected: state mismatch pending={pending_state!r} "
                f"returned={returned_state!r} is_web_runtime={is_web_runtime}"
            )
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
            if account_id:
                print(  # noqa: T201
                    f"[DEBUG-AUTH] update_account_tokens account_id={account_id} "
                    f"has_refresh_token={bool(query_params.get('refresh_token'))} "
                    f"expires_in={expires_in}"
                )
                self.update_account_tokens(
                    account_id,
                    access_token,
                    query_params.get("refresh_token", ""),
                    expires_in,
                )
            else:
                self.add_account(
                    email=email,
                    access_token=access_token,
                    refresh_token=query_params.get("refresh_token", ""),
                    expires_in=expires_in,
                )
        except ValueError as error:
            return {"ok": False, "message": str(error)}

        return {"ok": True, "message": f"Cuenta {email} vinculada"}
