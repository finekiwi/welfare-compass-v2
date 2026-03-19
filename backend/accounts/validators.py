import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    비밀번호 복잡도: 영문, 숫자, 특수문자 각각 1개 이상.
    """

    def validate(self, password, user=None):
        if not re.search(r"[A-Za-z]", password or ""):
            raise ValidationError(_("영문자를 1자 이상 포함해야 합니다."), code="password_no_letter")
        if not re.search(r"[0-9]", password or ""):
            raise ValidationError(_("숫자를 1자 이상 포함해야 합니다."), code="password_no_number")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password or ""):
            raise ValidationError(_("특수문자를 1자 이상 포함해야 합니다."), code="password_no_special")

    def get_help_text(self):
        return _("영문, 숫자, 특수문자를 각각 1자 이상 포함해야 합니다.")
