package com.qa.common;

public enum ErrorCode {
    SUCCESS(200, "success"),
    USERNAME_OR_PASSWORD_ERROR(1001, "用户名或密码错误"),
    USERNAME_EXISTS(1002, "用户名已存在"),
    TOKEN_EXPIRED(1003, "Token已过期"),
    TOKEN_INVALID(1004, "Token格式错误"),
    FILE_TYPE_NOT_SUPPORTED(2001, "文件类型不支持"),
    FILE_SIZE_EXCEEDED(2002, "文件大小超出限制"),
    DOCUMENT_INDEX_FAILED(2003, "文档索引失败"),
    DOCUMENT_NOT_FOUND(2004, "文档不存在"),
    NOT_FOUND(4004, "资源不存在"),
    AI_SERVICE_UNAVAILABLE(3001, "AI服务暂时不可用"),
    AI_TIMEOUT(3002, "AI服务响应超时"),
    FORBIDDEN(4003, "无权限访问"),
    INTERNAL_ERROR(5000, "服务器内部错误");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
