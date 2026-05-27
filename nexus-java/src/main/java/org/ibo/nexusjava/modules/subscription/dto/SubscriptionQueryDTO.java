package org.ibo.nexusjava.modules.subscription.dto;

import lombok.Data;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class SubscriptionQueryDTO {
    private String name;
    private Integer status;
    private Long current = 1L;
    private Long size = 10L;
}
