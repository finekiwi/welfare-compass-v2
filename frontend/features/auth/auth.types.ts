// features/auth/auth.types.ts
// 인증 관련 요청/응답 타입을 한 곳에서 관리하면
// 백엔드 변경 시 여기만 고치면 되어서 유지보수가 쉬워져요.

export type SignupRequest = {
    username: string;
    email?: string;
    password1: string; // dj-rest-auth requires password1
    password2: string;
    // 정책 알림 동의
    email_notification_consent?: boolean;
    notification_email?: string;
};

export type SignupResponse = {
    access?: string;
    refresh?: string;
    user: {
        pk: number;
        username: string;
        email: string;
        first_name?: string;
        last_name?: string;
    };
};

// simplejwt 기본 응답 형태: access, refresh
export type LoginRequest = {
    username: string;
    email?: string; // 이메일 로그인 지원 시
    password: string;
};

export type LoginResponse = {
    access: string;
    refresh: string;
    user: {
        pk: number;
        username: string;
        email: string;
        first_name?: string;
        last_name?: string;
    };
};
