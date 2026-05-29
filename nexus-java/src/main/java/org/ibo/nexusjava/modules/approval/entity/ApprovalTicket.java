package org.ibo.nexusjava.modules.approval.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("approval_ticket")
public class ApprovalTicket {
    @TableId(type = IdType.AUTO)
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
