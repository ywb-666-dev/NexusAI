package org.ibo.nexusjava.modules.audit.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class AuditLogVO {
    private Long id;
    private Long userId;
    private String action;
    private String targetType;
    private String targetId;
    private LocalDateTime actionTime;
    private String ipAddress;
    private String requestId;
}
