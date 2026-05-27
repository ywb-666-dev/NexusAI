package org.ibo.nexusjava.modules.content.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.ibo.nexusjava.modules.content.entity.Content;

@Mapper
public interface ContentMapper extends BaseMapper<Content> {
}