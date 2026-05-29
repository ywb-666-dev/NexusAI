package org.ibo.nexusjava.modules.system.vo;

import lombok.Data;

@Data
public class SystemMetricsVO {
    private Long totalUsers;
    private Long totalSubscriptions;
    private Long totalContents;
    private Long pendingApprovals;
}
