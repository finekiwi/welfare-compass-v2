// features/auth/auth.types.ts
// 인증 관련 요청/응답 타입을 한 곳에서 관리하면
// 백엔드 변경 시 여기만 고치면 되어서 유지보수가 쉬워져요.

export type SignupRequest = {
    username: string;
    email?: string;
    password: string;
    password2: string;
};

export type SignupResponse = {
    message: string;
    user: {
        username: string;
        email: string;
    };
};

// simplejwt 기본 응답 형태: access, refresh
export type LoginRequest = {
    username: string;
    password: string;
};

export type LoginResponse = {
    access: string;
    refresh: string;
};
