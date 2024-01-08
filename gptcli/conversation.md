 # {{data.topic}}                                                                                                                                                                                             
                                                                                                                                                                                                                
{% for message in data.messages %}                                                                                                                                                                             
**{{message.role}}**: 

{{message.content}}                                                                                                                                                                      
{% endfor %}      
