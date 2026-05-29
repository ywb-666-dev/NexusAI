package org.ibo.nexusjava.modules.approval.dto;

import lombok.Data;

@Data
public class ApprovalTicketDTO {
    private Long approvedBy;
    private String comment;
}
