package org.ibo.nexusjava.modules.audit.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.modules.audit.vo.AuditLogVO;

public interface AuditLogService {
    IPage<AuditLogVO> list(Long current, Long size);
}
