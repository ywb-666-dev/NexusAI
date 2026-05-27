package org.ibo.nexusjava.modules.subscription.vo;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionVO {
    private Long id;
    private String name;
    private List<String> keywords;
    private List<String> sourcePlatforms;
    private Integer matchMode;
    private String triggerConditions;
    private Integer priority;
    private Integer status;
    private String cronExpression;
    private LocalDateTime lastRunAt;
    private LocalDateTime createdAt;
}
