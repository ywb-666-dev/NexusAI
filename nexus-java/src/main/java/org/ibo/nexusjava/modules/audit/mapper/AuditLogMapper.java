package org.ibo.nexusjava.modules.audit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.ibo.nexusjava.modules.audit.entity.AuditLog;

@Mapper
public interface AuditLogMapper extends BaseMapper<AuditLog> {
}
