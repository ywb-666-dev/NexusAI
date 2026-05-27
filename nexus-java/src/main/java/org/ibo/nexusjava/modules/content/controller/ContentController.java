package org.ibo.nexusjava.modules.content.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.content.service.ContentService;
import org.ibo.nexusjava.modules.content.vo.ContentVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/java/contents")
public class ContentController {

    @Autowired
    private ContentService contentService;

    @GetMapping
    public Result<IPage<ContentVO>> list(
            @RequestParam(required = false) Long subscriptionId,
            @RequestParam(required = false, defaultValue = "1") Long current,
            @RequestParam(required = false, defaultValue = "10") Long size) {
        return Result.success(contentService.listBySubscription(subscriptionId, current, size));
    }

    @GetMapping("/{id}")
    public Result<ContentVO> getById(@PathVariable String id) {
        return Result.success(contentService.getById(id));
    }
}