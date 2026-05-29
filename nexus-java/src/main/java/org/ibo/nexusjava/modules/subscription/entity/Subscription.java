package org.ibo.nexusjava.modules.subscription.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
@TableName("subscription")
public class Subscription {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private String name;
    private String keywords;        // JSON数组字符串
    private String sourcePlatforms; // JSON数组字符串
    private Integer matchMode;      // 1=精确 2=模糊 3=语义
    private String triggerConditions; // JSON DSL
    private Integer priority;       // 1⾼ 2中 3低
    private Integer status;         // 0暂停 1启⽤
    private String cronExpression;
    private LocalDateTime lastRunAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
