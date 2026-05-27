package org.ibo.nexusjava.modules.subscription.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionDTO {
    @NotBlank(message = "规则名称不能为空")
    private String name;
    private List<String> keywords;
    private List<String> sourcePlatforms;
    private Integer matchMode;
    private String cronExpression;
    private Integer priority;
}
