package org.ibo.nexusjava.modules.audit.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.audit.service.AuditLogService;
import org.ibo.nexusjava.modules.audit.vo.AuditLogVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/java/audit-logs")
public class AuditLogController {

    @Autowired
    private AuditLogService auditLogService;

    @GetMapping
    public Result<IPage<AuditLogVO>> list(
            @RequestParam(required = false, defaultValue = "1") Long current,
            @RequestParam(required = false, defaultValue = "10") Long size) {
        return Result.success(auditLogService.list(current, size));
    }
}
