package org.ibo.nexusjava.modules.approval.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ApprovalTicketVO {
    private Long id;
    private String taskId;
    private Long userId;
    private String actionType;
    private Integer riskLevel;
    private String context;
    private Integer status;
    private Long approvedBy;
    private LocalDateTime approvedAt;
    private String comment;
    private LocalDateTime createdAt;
}
