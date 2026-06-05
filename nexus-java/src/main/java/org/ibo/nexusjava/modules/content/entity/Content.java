package org.ibo.nexusjava.modules.content.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("content")
public class Content {
    @TableId
    private String id;
    private Long subscriptionId;
    private String sourcePlatform;
    private String sourceUrl;
    private String title;
    private String summary;
    private String contentBody;
    private String author;
    private LocalDateTime publishedAt;
    private LocalDateTime fetchedAt;
    private String contentHash;
    private String vectorId;
    private Integer status;
    private Integer isDuplicate;
    private String duplicateOf;
    private String relatedContents; // JSON
    private LocalDateTime createdAt;
}